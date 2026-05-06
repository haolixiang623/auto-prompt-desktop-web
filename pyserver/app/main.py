from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import re
import select
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.paths import get_paths
from .core.data import DataStore
from .core.excel_parser import parse_excel_for_cases, parse_excel_for_review_rules
from .factors_repair_suggestions import (
    apply_factors_repair_suggestion_patches,
    generate_factors_repair_suggestions,
)
from .factors_workbook import load_factors_workbook, save_factors_workbook
from .factor_prompt_artifacts import build_preview_prompt, load_factor_prompt_artifact, save_factor_prompt_artifact
from .review_rule_builtin_variables import normalize_review_rule_builtin_variables
from .workspace_validation import (
    collect_workspace_material_dirs,
    collect_workspace_sample_files,
    validate_workspace_bundle,
)


OPENAI_COMPAT_BASE_URL = "https://api.openai.com/v1"
DASHSCOPE_COMPAT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

DEFAULT_MODELS = [
    {"id": "1", "name": "Qwen VL Max", "model": "qwen-vl-max", "base_url": DASHSCOPE_COMPAT_BASE_URL, "api_key": "", "type": "vl", "params": []},
    {"id": "2", "name": "Qwen VL Plus", "model": "qwen-vl-plus", "base_url": DASHSCOPE_COMPAT_BASE_URL, "api_key": "", "type": "vl", "params": []},
    {"id": "3", "name": "Qwen2.5 VL 72B", "model": "qwen2.5-vl-72b-instruct", "base_url": DASHSCOPE_COMPAT_BASE_URL, "api_key": "", "type": "vl", "params": []},
    {"id": "4", "name": "Qwen Plus (Text)", "model": "qwen-plus", "base_url": DASHSCOPE_COMPAT_BASE_URL, "api_key": "", "type": "text", "params": []},
    {"id": "5", "name": "Qwen Max (Text)", "model": "qwen-max", "base_url": DASHSCOPE_COMPAT_BASE_URL, "api_key": "", "type": "text", "params": []},
]

DEFAULT_EXTRACT_PROMPT_TEMPLATE = """# 角色与核心指令
你是一个高精度的文本提取器。你的唯一任务是从用户提供的材料中，逐字逐句地定位并返回指定的要素文本内容。你必须遵守以下铁律：
1. **严格忠于原文**：只返回材料中明确出现的文本片段，不做任何推断、总结、解释或补全。如果材料中没有对应内容，必须返回""。
2. **禁止联想**：绝对禁止基于常识或外部知识添加任何材料中不存在的信息。

# 要素识别规范
统一要求：
- 识别到相关要素，但要素值未填写，则返回value为空，但需返回具体要素的bbox坐标；若未识别的相关要素字段则跳过该要素、无需返回到输出的msginfo中
- 对于需要返回的要素，需返回 name（要素名称）、value（识别值过滤空格）、bbox（坐标格式 [x1,y1,x2,y2]，以左上角为基准）
- 未识别时 value 和 bbox 返回空字符串
- 坐标需保持识别一致性
- 最终返回的要素名称用序号代替

# 识别要素列表及规则
$(factors)

# 输出格式要求
请严格按照以下JSON格式输出，
{
  "msginfo": [
    {"name": "1", "value": "要素值", "bbox": [x1,y1,x2,y2]}
  ]
}
**无需返回分析过程，直接输出JSON代码块。**
"""

DEFAULT_ANALYSIS_PROMPT_TEMPLATE = """请仔细分析这张图片，识别以下要素的内容：
{{factor_list}}

对于每个要素，请提取其在图片中的实际值。如果某个要素不存在，请说明。
请以JSON格式返回，格式如下：
{
  "factors": [
    {"name": "要素名称", "value": "识别到的值", "exists": true}
  ]
}"""

DEFAULT_RULE_PROMPT_TEMPLATE = """基于以下要素识别结果和用户提供的说明，为每个要素生成精准的提取规则和格式要求。

要素列表及说明：
{{factor_context}}

识别结果（仅用于理解要素的位置和上下文，不得将具体数值写入规则）：
{{analysis_result}}

请为每个要素生成：
1. **提取规则**：描述如何在同类文档中定位和识别该要素（结合用户提供的提取说明和规则说明）
2. **格式要求**：描述提取后的格式处理要求（参考用户的规则说明）

**泛化要求（重要）**：
- 提取规则必须具备通用性，适用于同类型的所有文档，而不仅针对本次识别到的具体文档
- 禁止在规则中出现具体的数值、金额、日期、名称、编号等特定文档才有的内容
- 规则描述应基于要素的结构特征和位置规律（如"位于文档抬头"、"表格第X列"、"盖章处下方"等）
- 可描述数据类型特征（如"数字"、"日期格式"、"中文名称"），但不能写具体值
- 格式要求要明确，参考用户的规则说明，如果不需要格式处理则说明"保持原格式"

请以JSON格式返回：
{
  "factors": [
    {
      "name": "要素名称",
      "rule": "通用的提取规则描述（不含具体值）",
      "format": "格式要求描述"
    }
  ]
}"""

BROKEN_DEFAULT_ANALYSIS_PROMPT_TEMPLATE = "请结合以下要素上下文识别样本文档中每个要素的实际位置、结构特征和可见值：\n{{factor_context}}"
BROKEN_DEFAULT_RULE_PROMPT_TEMPLATE = "基于识别结果为每个未命中要素生成可泛化的 factor_prompt，禁止写样本中的具体值。\n识别结果：\n{{analysis_result}}"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_model_entry(raw: Any) -> dict[str, Any]:
    entry = raw if isinstance(raw, dict) else {}
    model = str(entry.get("model") or entry.get("model_id") or entry.get("model_name") or "").strip()
    name = str(entry.get("name") or model or "未命名模型").strip()
    legacy_style = "model_id" in entry or "base_url" not in entry
    default_base_url = DASHSCOPE_COMPAT_BASE_URL if legacy_style else OPENAI_COMPAT_BASE_URL
    base_url = str(entry.get("base_url") or entry.get("api_base") or default_base_url).strip() or default_base_url
    api_key = str(entry.get("api_key") or "").strip()
    model_type = str(entry.get("type") or "vl").strip() or "vl"
    params = entry.get("params")
    if not isinstance(params, (list, dict)):
        params = []
    return {
        "id": str(entry.get("id") or ""),
        "name": name,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "type": model_type,
        "params": params,
    }


def normalize_models(raw_models: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_models, list):
        raw_models = []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_models, start=1):
        entry = normalize_model_entry(item)
        if not entry["id"]:
            entry["id"] = str(index)
        normalized.append(entry)
    return normalized


def default_extract_profile(system_prompt: str | None = None) -> dict[str, Any]:
    return {
        "id": "gov-default",
        "name": "政务通用规则",
        "unmatchedStrategy": "ai_generate",
        "systemPrompt": str(system_prompt or PromptBundle.extract).strip(),
        "analysisPromptTemplate": DEFAULT_ANALYSIS_PROMPT_TEMPLATE,
        "generationPromptTemplate": DEFAULT_RULE_PROMPT_TEMPLATE,
        "promptTemplate": DEFAULT_EXTRACT_PROMPT_TEMPLATE,
    }


def normalize_extract_profile(raw_profile: Any, fallback_system_prompt: str | None = None) -> dict[str, Any]:
    base = default_extract_profile(fallback_system_prompt)
    profile = raw_profile if isinstance(raw_profile, dict) else {}
    analysis_prompt_template = str(profile.get("analysisPromptTemplate") or base["analysisPromptTemplate"]).strip() or base["analysisPromptTemplate"]
    generation_prompt_template = str(profile.get("generationPromptTemplate") or base["generationPromptTemplate"]).strip() or base["generationPromptTemplate"]
    if analysis_prompt_template == BROKEN_DEFAULT_ANALYSIS_PROMPT_TEMPLATE:
        analysis_prompt_template = DEFAULT_ANALYSIS_PROMPT_TEMPLATE
    if generation_prompt_template == BROKEN_DEFAULT_RULE_PROMPT_TEMPLATE:
        generation_prompt_template = DEFAULT_RULE_PROMPT_TEMPLATE
    normalized = {
        "id": str(profile.get("id") or base["id"]).strip() or base["id"],
        "name": str(profile.get("name") or base["name"]).strip() or base["name"],
        "unmatchedStrategy": str(profile.get("unmatchedStrategy") or base["unmatchedStrategy"]).strip() or base["unmatchedStrategy"],
        "systemPrompt": str(profile.get("systemPrompt") or fallback_system_prompt or base["systemPrompt"]).strip(),
        "analysisPromptTemplate": analysis_prompt_template,
        "generationPromptTemplate": generation_prompt_template,
        "promptTemplate": str(profile.get("promptTemplate") or base["promptTemplate"]).strip() or base["promptTemplate"],
    }
    return normalized


def normalize_extract_profiles(raw_profiles: Any, fallback_system_prompt: str | None = None) -> list[dict[str, Any]]:
    if not isinstance(raw_profiles, list) or not raw_profiles:
        return [default_extract_profile(fallback_system_prompt)]
    normalized = [normalize_extract_profile(item, fallback_system_prompt) for item in raw_profiles]
    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for profile in normalized:
        if profile["id"] in seen_ids:
            continue
        seen_ids.add(profile["id"])
        deduped.append(profile)
    return deduped or [default_extract_profile(fallback_system_prompt)]


def fail(status: int, message: str) -> None:
    raise HTTPException(status_code=status, detail=message)


def user_to_json(user: Any) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "active": bool(user.active),
        "createdAt": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
    }


def workspace_to_json(summary: Any) -> dict[str, Any]:
    return {
        "id": summary.id,
        "name": summary.name,
        "rootPath": summary.root_path,
        "createdAt": summary.created_at.isoformat() if hasattr(summary.created_at, "isoformat") else str(summary.created_at),
        "files": [
            {"relativePath": item.relative_path, "size": item.size, "isDir": item.is_dir}
            for item in summary.files
        ],
    }


PASSWORD_HASHER = PasswordHasher()
SESSION_TTL = timedelta(days=1)


# ─────────────────── LLM 调用日志存储（内存，最多2000条） ───────────────────

class LlmLogStore:
    MAX_ENTRIES = 2000

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._counter = 0
        self._lock = threading.Lock()

    def add(self, *, scene: str, model: str, prompt_summary: str,
            response_summary: str = "", error: str = "",
            success: bool = True, elapsed_s: Optional[float] = None) -> None:
        with self._lock:
            self._counter += 1
            entry = {
                "id": self._counter,
                "scene": scene,
                "model": model,
                "prompt_summary": prompt_summary[:2000],
                "response_summary": response_summary[:2000],
                "error": error[:2000] if error else "",
                "success": success,
                "elapsed_s": round(elapsed_s, 1) if elapsed_s is not None else None,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._entries.append(entry)
            if len(self._entries) > self.MAX_ENTRIES:
                self._entries = self._entries[-self.MAX_ENTRIES:]

    def list(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            # 最新的在前
            sorted_entries = list(reversed(self._entries))
            start = (page - 1) * page_size
            end = start + page_size
            return {
                "entries": sorted_entries[start:end],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._counter = 0


class UploadedBlob(BaseModel):
    original_name: str
    relative_path: str
    content: bytes


class WorkspaceFile(BaseModel):
    relative_path: str
    size: int
    is_dir: bool


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    root_path: str
    created_at: datetime
    files: list[WorkspaceFile]


class WorkspaceService:
    def __init__(self, paths: Any):
        self.paths = paths

    def _user_workspace_root(self, user_id: str) -> Path:
        root = self.paths.workspace_root / user_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _user_upload_root(self, user_id: str) -> Path:
        root = self.paths.upload_root / user_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _sanitize(self, relative_path: str) -> str:
        path = Path(relative_path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("invalid relative path")
        return path.as_posix()

    def _shared_prefix(self, uploads: list[UploadedBlob]) -> Optional[str]:
        prefix = None
        for upload in uploads:
            parts = [part for part in upload.relative_path.replace("\\", "/").split("/") if part]
            if len(parts) < 2:
                return None
            current = parts[0]
            if prefix is None:
                prefix = current
            elif prefix != current:
                return None
        return prefix

    def _scan(self, root: Path) -> list[WorkspaceFile]:
        files = []
        for entry in root.rglob("*"):
            files.append(WorkspaceFile(relative_path=entry.relative_to(root).as_posix(), size=entry.stat().st_size, is_dir=entry.is_dir()))
        files.sort(key=lambda item: item.relative_path)
        return files

    def create_workspace(self, user_id: str, name: Optional[str] = None, uploads: Optional[list[UploadedBlob]] = None) -> WorkspaceSummary:
        uploads = uploads or []
        workspace_id = str(uuid4())
        root = self._user_workspace_root(user_id) / workspace_id
        root.mkdir(parents=True, exist_ok=True)
        prefix = self._shared_prefix(uploads)
        for upload in uploads:
            relative_path = upload.relative_path
            if prefix and relative_path.replace("\\", "/").startswith(f"{prefix}/"):
                relative_path = relative_path.replace("\\", "/")[len(prefix) + 1:]
            target = root / self._sanitize(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(upload.content)
        return WorkspaceSummary(id=workspace_id, name=name or f"workspace-{workspace_id}", root_path=str(root), created_at=datetime.utcnow(), files=self._scan(root))

    def get_workspace(self, user_id: str, workspace_id: str) -> WorkspaceSummary:
        root = self._user_workspace_root(user_id) / workspace_id
        if not root.exists():
            raise ValueError("workspace not found")
        return WorkspaceSummary(id=workspace_id, name=f"workspace-{workspace_id}", root_path=str(root), created_at=datetime.fromtimestamp(root.stat().st_ctime), files=self._scan(root))

    def list_workspaces(self, user_id: str, module: Optional[str] = None) -> list[dict[str, Any]]:
        root = self._user_workspace_root(user_id)
        result = []
        for entry in sorted(root.iterdir(), key=lambda p: p.stat().st_ctime, reverse=True):
            if not entry.is_dir():
                continue
            ws_id = entry.name
            module_file = entry / ".module"
            ws_module = module_file.read_text().strip() if module_file.exists() else ""
            status_file = entry / ".gen_status"
            gen_status = ""
            if status_file.exists():
                try:
                    gen_status = status_file.read_text().strip()
                except Exception:
                    pass
            # 兼容历史数据：旧版要素生成可能只写入了 .gen_status，未及时写 .module
            if module and ws_module != module:
                if not (module == "generate" and gen_status):
                    continue
            ctime = datetime.fromtimestamp(entry.stat().st_ctime)
            # 统计顶级子目录（即材料文件夹）
            materials = [d.name for d in sorted(entry.iterdir()) if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("__")]
            total_files = sum(1 for _ in entry.rglob("*") if _.is_file())
            result.append({
                "id": ws_id,
                "rootPath": str(entry),
                "createdAt": ctime.isoformat(),
                "module": ws_module,
                "materials": materials,
                "materialCount": len(materials),
                "fileCount": total_files,
                "genStatus": gen_status,
            })
        return result

    def tag_workspace(self, user_id: str, workspace_id: str, module: str) -> bool:
        root = self._user_workspace_root(user_id) / workspace_id
        if not root.exists() or not root.is_dir():
            return False
        (root / ".module").write_text(module)
        return True

    def update_workspace_activity(
        self,
        user_id: str,
        workspace_id: str,
        module: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        root = self._user_workspace_root(user_id) / workspace_id
        if not root.exists() or not root.is_dir():
            return False

        if module is not None:
            module_file = root / ".module"
            if module:
                module_file.write_text(module)
            elif module_file.exists():
                module_file.unlink()

        if status is not None:
            status_file = root / ".gen_status"
            if status:
                status_file.write_text(status)
            elif status_file.exists():
                status_file.unlink()

        return True

    def delete_workspace(self, user_id: str, workspace_id: str) -> bool:
        import shutil
        root = self._user_workspace_root(user_id) / workspace_id
        if not root.exists() or not root.is_dir():
            return False
        shutil.rmtree(root)
        return True

    def save_temp_uploads(self, user_id: str, uploads: list[UploadedBlob]) -> list[str]:
        root = self._user_upload_root(user_id) / str(uuid4())
        root.mkdir(parents=True, exist_ok=True)
        result = []
        for upload in uploads:
            target = root / self._sanitize(upload.relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(upload.content)
            result.append(str(target))
        return result


class AuthStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)")
            conn.commit()
        self._purge_expired_sessions()
        self._ensure_admin()

    def _ensure_admin(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
            if row is not None:
                return
            conn.execute(
                "INSERT INTO users (id, name, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(16), "System Admin", "admin", PASSWORD_HASHER.hash("admin123456"), "admin", 1, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def _row_to_user(self, row: Any) -> Any:
        return type("User", (), {
            "id": row[0],
            "name": row[1],
            "username": row[2],
            "role": type("Role", (), {"value": row[3]})(),
            "active": bool(row[4]),
            "created_at": datetime.fromisoformat(row[5]),
        })()

    def authenticate(self, username: str, password: str) -> Any:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT id, name, username, role, active, created_at, password_hash FROM users WHERE username = ?", (username,)).fetchone()
            if row is None or not bool(row[4]):
                return None
            try:
                valid = PASSWORD_HASHER.verify(row[6], password)
            except VerifyMismatchError:
                valid = False
            return self._row_to_user(row[:6]) if valid else None

    def _purge_expired_sessions(self, now: Optional[datetime] = None) -> None:
        expires_before = (now or datetime.utcnow()).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (expires_before,))
            conn.commit()

    def create_session(self, user: Any, remember_me: bool = False) -> dict[str, str]:
        token = secrets.token_urlsafe(32)
        created_at = datetime.utcnow()
        # 登录态统一保留 1 天；是否“记住登录”由前端决定写入 sessionStorage 还是 localStorage。
        expires_at = created_at + SESSION_TTL
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (token, user.id, expires_at.isoformat(), created_at.isoformat()),
            )
            conn.commit()
        return {"token": token, "expires_at": expires_at.isoformat()}

    def get_user_from_token(self, token: str) -> Any:
        self._purge_expired_sessions()
        with sqlite3.connect(str(self.db_path)) as conn:
            session_row = conn.execute("SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
            if session_row is None:
                return None

            if session_row[1] <= datetime.utcnow().isoformat():
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None

            row = conn.execute(
                "SELECT id, name, username, role, active, created_at FROM users WHERE id = ?",
                (session_row[0],),
            ).fetchone()
            if row is None or not bool(row[4]):
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None
            return self._row_to_user(row)

    def delete_session(self, token: str) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()

    def delete_sessions_for_user(self, user_id: str) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.commit()

    def list_users(self) -> list[Any]:
        with sqlite3.connect(str(self.db_path)) as conn:
            return [self._row_to_user(row) for row in conn.execute("SELECT id, name, username, role, active, created_at FROM users ORDER BY created_at").fetchall()]

    def create_user(self, req: Any) -> Any:
        user_id = secrets.token_hex(16)
        created_at = datetime.utcnow().isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO users (id, name, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, req.name, req.username, PASSWORD_HASHER.hash(req.password), "user", 1, created_at),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("user already exists") from exc
            conn.commit()
            row = conn.execute("SELECT id, name, username, role, active, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_user(row)

    def reset_password(self, user_id: str, password: str) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (PASSWORD_HASHER.hash(password), user_id))
            conn.commit()
            updated = cursor.rowcount > 0
        if updated:
            self.delete_sessions_for_user(user_id)
        return updated

    def update_user_status(self, user_id: str, active: bool) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
            conn.commit()
            updated = cursor.rowcount > 0
        if updated and not active:
            self.delete_sessions_for_user(user_id)
        return updated


class TaskCancelledError(Exception):
    """Raised when a background task is cancelled by the user."""


class TaskStore:
    def __init__(self, task_root: Path):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._logs: dict[str, list[str]] = {}
        self._cancel_requested: set[str] = set()
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, owner_user_id: str, data_store: Any = None):
        task_id = str(uuid4())
        task = type("Task", (), {
            "id": task_id,
            "kind": kind,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "owner_user_id": owner_user_id,
            "model_dump": lambda self=None: {"id": task_id, "kind": kind, "status": self.status if self else "pending", "progress": self.progress if self else 0, "result": self.result if self else None, "error": self.error if self else None},
        })()
        with self._lock:
            self._tasks[task_id] = task
            self._logs[task_id] = []
        return task

    def get(self, task_id: str, owner_user_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            return task if task and task.owner_user_id == owner_user_id else None

    def logs(self, task_id: str, owner_user_id: str):
        task = self.get(task_id, owner_user_id)
        if not task:
            return None
        with self._lock:
            return list(self._logs.get(task_id, []))

    def mark_running(self, task_id: str, progress: int = 0):
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status not in {"succeeded", "failed", "cancelled"}:
                task.status = "running"
                task.progress = progress

    def append_log(self, task_id: str, line: str):
        with self._lock:
            if task_id in self._logs:
                self._logs[task_id].append(line)

    def complete(self, task_id: str, result: Any):
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status not in {"succeeded", "failed", "cancelled"}:
                task.status = "succeeded"
                task.progress = 100
                task.result = result
                task.error = None
            self._cancel_requested.discard(task_id)
            self._processes.pop(task_id, None)

    def fail(self, task_id: str, error: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status not in {"succeeded", "failed", "cancelled"}:
                task.status = "failed"
                task.error = error
            self._cancel_requested.discard(task_id)
            self._processes.pop(task_id, None)

    def mark_cancelled(self, task_id: str, error: str = "已停止生成"):
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status not in {"succeeded", "failed", "cancelled"}:
                task.status = "cancelled"
                task.error = error
            self._cancel_requested.discard(task_id)
            self._processes.pop(task_id, None)

    def request_cancel(self, task_id: str, owner_user_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.owner_user_id != owner_user_id:
                return None
            if task.status in {"succeeded", "failed", "cancelled"}:
                return task
            self._cancel_requested.add(task_id)
            process = self._processes.get(task_id)
        if process is not None:
            _terminate_process(process)
        return task

    def is_cancel_requested(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancel_requested

    def register_process(self, task_id: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._processes[task_id] = process

    def unregister_process(self, task_id: str, process: Optional[subprocess.Popen[str]] = None) -> None:
        with self._lock:
            current = self._processes.get(task_id)
            if process is None or current is process:
                self._processes.pop(task_id, None)


@dataclass
class PromptBundle:
    classify: str = "Optimize classification prompts."
    extract: str = "Generate generalized extraction prompts."


class UiSettingsStore:
    FRONT_FIELDS = (
        "api_key",
        "default_model_id",
        "model_name",
        "models",
        "god_prompt",
        "extract_god_prompt",
        "extract_profiles",
        "default_extract_profile_id",
        "review_rule_builtin_variables",
        "llm_timeout",
    )

    def __init__(self, local_path: Path, project_path: Path) -> None:
        self.local_path = local_path
        self.project_path = project_path

    def _models_need_migration(self, data: Any) -> bool:
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list):
            return False
        for model in models:
            if not isinstance(model, dict):
                continue
            if "model_id" in model:
                return True
            if "model" not in model or "base_url" not in model or "api_key" not in model:
                return True
        return False

    def load_front(self) -> dict[str, Any]:
        project = load_json(self.project_path, {})
        local = load_json(self.local_path, {})
        fallback_api_key = (
            local.get("api_key")
            or project.get("api_key")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("DASHSCOPE_API_KEY", "")
        )
        project_models = normalize_models(project.get("models", DEFAULT_MODELS))
        local_models = normalize_models(local.get("models", project_models))
        default_model_id = local.get("default_model_id", project.get("default_model_id", local_models[0]["id"] if local_models else "1"))
        model_name = local.get("model_name", project.get("model_name", local_models[0]["model"] if local_models else ""))
        legacy_extract_prompt = local.get("extract_god_prompt", project.get("extract_god_prompt", PromptBundle.extract))
        project_extract_profiles = normalize_extract_profiles(
            project.get("extract_profiles"),
            project.get("extract_god_prompt", PromptBundle.extract),
        )
        raw_local_extract_profiles = local.get("extract_profiles")
        if raw_local_extract_profiles is None:
            raw_local_extract_profiles = project.get("extract_profiles")
        local_extract_profiles = normalize_extract_profiles(raw_local_extract_profiles, legacy_extract_prompt)
        default_extract_profile_id = local.get(
            "default_extract_profile_id",
            project.get("default_extract_profile_id", local_extract_profiles[0]["id"] if local_extract_profiles else default_extract_profile()["id"]),
        )
        settings = {
            "api_key": local["api_key"] if "api_key" in local else fallback_api_key,
            "api_key_configured": False,
            "default_model_id": default_model_id,
            "model_name": model_name,
            "models": local_models or normalize_models(DEFAULT_MODELS),
            "god_prompt": local.get("god_prompt", project.get("god_prompt", PromptBundle.classify)),
            "extract_god_prompt": legacy_extract_prompt,
            "extract_profiles": local_extract_profiles,
            "default_extract_profile_id": default_extract_profile_id,
            "review_rule_builtin_variables": normalize_review_rule_builtin_variables(
                local.get("review_rule_builtin_variables", project.get("review_rule_builtin_variables"))
            ),
            "llm_timeout": local.get("llm_timeout", project.get("llm_timeout", 120)),
        }
        settings["api_key_configured"] = bool(
            settings["api_key"] or any(str(model.get("api_key", "")).strip() for model in settings["models"])
        )
        selected = next((m for m in settings["models"] if m.get("id") == settings["default_model_id"]), None)
        if selected:
            settings["model_name"] = selected.get("model", settings["model_name"])
        if self.local_path.exists() and self._models_need_migration(local):
            write_json(self.local_path, {field: settings[field] for field in self.FRONT_FIELDS})
        return settings

    def save_front(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_front()
        current.update({k: v for k, v in payload.items() if k in self.FRONT_FIELDS})
        current["models"] = normalize_models(current.get("models"))
        current["extract_profiles"] = normalize_extract_profiles(
            current.get("extract_profiles"),
            current.get("extract_god_prompt"),
        )
        current["review_rule_builtin_variables"] = normalize_review_rule_builtin_variables(
            current.get("review_rule_builtin_variables")
        )
        extract_default = next(
            (profile for profile in current["extract_profiles"] if profile.get("id") == current.get("default_extract_profile_id")),
            None,
        )
        if extract_default is None and current["extract_profiles"]:
            current["default_extract_profile_id"] = current["extract_profiles"][0]["id"]
            current["extract_god_prompt"] = current["extract_profiles"][0]["systemPrompt"]
        elif extract_default is not None:
            current["extract_god_prompt"] = extract_default["systemPrompt"]
        selected = next((m for m in current["models"] if m.get("id") == current.get("default_model_id")), None)
        if selected:
            current["model_name"] = selected.get("model", current.get("model_name", ""))
        current["api_key_configured"] = bool(
            current["api_key"] or any(str(model.get("api_key", "")).strip() for model in current["models"])
        )
        write_json(self.local_path, {field: current[field] for field in self.FRONT_FIELDS})
        return current

    def default_god_prompts(self) -> dict[str, str]:
        return {"classify": PromptBundle.classify, "extract": PromptBundle.extract}

    def test_api_key(self, api_key: str) -> None:
        if not api_key or len(api_key.strip()) < 10:
            raise ValueError("Invalid API key")


class LoginRequest(BaseModel):
    username: str
    password: str
    rememberMe: bool = False


class CreateUserRequest(BaseModel):
    name: str
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    password: str


class UpdateUserStatusRequest(BaseModel):
    active: bool


class SavePromptRequest(BaseModel):
    filePath: str
    content: str


class SaveArtifactRequest(BaseModel):
    filePath: str
    artifact: dict[str, Any]
    previewFilePath: Optional[str] = None


def _convert_pdf_first_page(pdf_path: Path, output_dir: Path) -> Optional[Path]:
    """Convert the first page of a PDF to a PNG image."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = pdf_path.stem
    out_path = output_dir / f"{base_name}_p1.png"
    if out_path.exists():
        return out_path
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            doc.close()
            return None
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        pix.save(str(out_path))
        doc.close()
        return out_path
    except ImportError:
        pass
    try:
        from pdf2image import convert_from_path
        imgs = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)
        if imgs:
            imgs[0].save(str(out_path), "PNG")
            return out_path
    except ImportError:
        pass
    return None


def find_media_file(material_dir: Path) -> Optional[Path]:
    """Find the first image file in the material directory (recursive search).
    If only PDF files exist, auto-convert the first page to an image."""
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    first_pdf: Optional[Path] = None
    for path in sorted(material_dir.rglob("*")):
        if path.is_file():
            if path.suffix.lower() in image_exts:
                return path
            if first_pdf is None and path.suffix.lower() == ".pdf":
                first_pdf = path
    if first_pdf is not None:
        converted = _convert_pdf_first_page(first_pdf, material_dir / "__pdf_converted__")
        if converted:
            return converted
    return None


_DASHSCOPE_BODY_PARAMS = {
    "enable_thinking",
    "thinking_budget",
    "translation_options",
    "vl_high_resolution_images",
    "search_options",
}


def normalize_model_params(params: Any) -> dict[str, Any]:
    if isinstance(params, dict):
        return {str(key).strip(): value for key, value in params.items() if str(key).strip()}
    if isinstance(params, list):
        normalized: dict[str, Any] = {}
        for item in params:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            if not key:
                continue
            normalized[key] = item.get("value")
        return normalized
    return {}


def resolve_model_config(settings: dict[str, Any], model_cfg_id: Optional[str]) -> dict[str, Any]:
    selected = None
    models = normalize_models(settings.get("models", []))
    if model_cfg_id:
        selected = next((m for m in models if m.get("id") == model_cfg_id), None)
    if selected is None:
        default_model_id = settings.get("default_model_id")
        if default_model_id:
            selected = next((m for m in models if m.get("id") == default_model_id), None)

    model_name = settings.get("model_name", "")
    api_key = str(settings.get("api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", "")).strip()
    base_url = OPENAI_COMPAT_BASE_URL
    params: dict[str, Any] = {}
    if selected:
        model_name = selected.get("model", model_name) or model_name
        api_key = str(selected.get("api_key") or api_key).strip()
        base_url = str(selected.get("base_url") or base_url).strip() or base_url
        params = normalize_model_params(selected.get("params"))
    elif model_name:
        base_url = DASHSCOPE_COMPAT_BASE_URL

    return {
        "id": selected.get("id") if selected else None,
        "model": model_name,
        "model_id": model_name,
        "api_key": api_key,
        "base_url": base_url,
        "params": params,
        "type": selected.get("type") if selected else None,
        "name": selected.get("name") if selected else None,
    }


def resolve_model_id(settings: dict[str, Any], model_cfg_id: Optional[str]) -> str:
    """Resolve a modelCfgId (string id from frontend) to the actual model_id string."""
    return resolve_model_config(settings, model_cfg_id)["model_id"]


def suggest_review_rule_description_with_model(
    settings: dict[str, Any],
    model_cfg_id: Optional[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    model_config = resolve_model_config(settings, model_cfg_id)
    if not model_config["model"]:
        raise ValueError("未配置可用的文本模型")
    if not model_config["api_key"]:
        raise ValueError("未配置可用的 API Key")

    factor_name = str(context.get("factorName") or "").strip()
    keypoint_name = str(context.get("keypointName") or "").strip()
    material_name = str(context.get("materialName") or "").strip()
    builtin_tokens = [str(item).strip() for item in (context.get("builtinVariableTokens") or []) if str(item).strip()]
    factor_candidates = [str(item).strip() for item in (context.get("factorCandidates") or []) if str(item).strip()]

    prompt = f"""你是 factors.xlsx 修复台里的规则说明修复助手。请只为单行“审查要点规则说明为空”的情况生成一个候选规则说明。

## 约束
1. 只能给出候选建议，不能假装已经保存。
2. 不得修改材料名称。
3. 不得修改既有要素定义名称。
4. 如果引用要素，优先使用当前材料下已有要素；当候选要素名存在时，可使用 #要素名称# 简写。
5. 允许使用已维护的内置变量：{", ".join(builtin_tokens) if builtin_tokens else "无"}
6. 输出必须是严格 JSON，不要附加解释。

## 当前行上下文
- 材料名称: {material_name or "未提供"}
- 审查要点名称: {keypoint_name or "未提供"}
- 推测相关要素: {factor_name or "未提供"}
- 当前材料已有要素: {", ".join(factor_candidates) if factor_candidates else "未提供"}

## 输出格式
{{
  "content": "候选规则说明文本",
  "reason": "一句话说明为什么这样建议",
  "confidence": 0.0
}}"""

    from openai import OpenAI

    request_kwargs = {
        "model": model_config["model"],
        "messages": [{"role": "user", "content": prompt}],
        **split_dashscope_extra_params(model_config.get("params")),
    }
    if "temperature" not in request_kwargs:
        request_kwargs["temperature"] = 0.2
    if "max_tokens" not in request_kwargs and "max_completion_tokens" not in request_kwargs:
        request_kwargs["max_tokens"] = 320

    client = OpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"],
        timeout=float(settings.get("llm_timeout", 120)),
    )
    response = client.chat.completions.create(**request_kwargs)
    content = ""
    try:
        content = response.choices[0].message.content or ""
    except Exception:
        content = ""

    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError("模型响应中未找到 JSON")
    payload = json.loads(match.group())
    return {
        "content": str(payload.get("content") or "").strip(),
        "reason": str(payload.get("reason") or "").strip(),
        "confidence": float(payload.get("confidence") or 0.0),
    }


def resolve_extract_profile(settings: dict[str, Any], rule_profile_id: Optional[str]) -> dict[str, Any]:
    profiles = normalize_extract_profiles(
        settings.get("extract_profiles"),
        settings.get("extract_god_prompt"),
    )
    selected_id = rule_profile_id or settings.get("default_extract_profile_id")
    if selected_id:
        selected = next((profile for profile in profiles if profile.get("id") == selected_id), None)
        if selected is None:
            raise ValueError(f"extract profile not found: {selected_id}")
        return selected
    return profiles[0]


def split_dashscope_extra_params(extra_params: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not extra_params:
        return {}
    standard = {k: v for k, v in extra_params.items() if k not in _DASHSCOPE_BODY_PARAMS}
    body = {k: v for k, v in extra_params.items() if k in _DASHSCOPE_BODY_PARAMS}
    if body:
        standard["extra_body"] = body
    return standard


def test_model_connection(model: dict[str, Any], fallback_api_key: str = "", timeout: int = 30) -> dict[str, Any]:
    normalized = normalize_model_entry(model)
    model_name = normalized.get("model", "").strip()
    base_url = normalized.get("base_url", "").strip() or OPENAI_COMPAT_BASE_URL
    api_key = normalized.get("api_key", "").strip() or str(fallback_api_key or "").strip()

    if not model_name:
        raise ValueError("模型配置缺少 model")
    if not base_url:
        raise ValueError("模型配置缺少 base_url")
    if not api_key:
        raise ValueError("模型配置缺少可用的 API Key")

    from openai import OpenAI

    request_kwargs = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        **split_dashscope_extra_params(normalize_model_params(normalized.get("params"))),
    }
    if "max_tokens" not in request_kwargs and "max_completion_tokens" not in request_kwargs:
        request_kwargs["max_tokens"] = 16
    if "temperature" not in request_kwargs:
        request_kwargs["temperature"] = 0

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=float(timeout))
    start = time.time()
    response = client.chat.completions.create(**request_kwargs)
    elapsed_s = time.time() - start
    preview = ""
    try:
        preview = response.choices[0].message.content or ""
    except Exception:
        preview = ""

    return {
        "ok": True,
        "model": model_name,
        "base_url": base_url,
        "elapsed_s": round(elapsed_s, 2),
        "preview": preview[:200],
    }


def base64_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run_verify_extraction(
    material_dir: Path,
    prompt_text: str,
    model_id: str,
    api_key: str,
    base_url: str = OPENAI_COMPAT_BASE_URL,
    extra_params: Optional[dict[str, Any]] = None,
    llm_logs: Optional[LlmLogStore] = None,
) -> dict[str, Any]:
    """Call Qwen VL to extract data from the first image using the given prompt."""
    image_path = find_media_file(material_dir)
    if image_path is None:
        return {"success": False, "error": "no image found in material directory"}

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    start = time.time()
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image(image_path)}"},
                        },
                    ],
                }
            ],
            **split_dashscope_extra_params(extra_params),
        )
        elapsed_s = time.time() - start
        output = response.choices[0].message.content
        if llm_logs:
            llm_logs.add(scene="验证提取", model=model_id, prompt_summary=prompt_text,
                         response_summary=output or "", success=True, elapsed_s=elapsed_s)
        return {
            "success": True,
            "image_file": image_path.name,
            "extraction_output": output,
            "error": None,
            "elapsed": f"{elapsed_s:.1f}",
        }
    except Exception as exc:
        elapsed_s = time.time() - start
        if llm_logs:
            llm_logs.add(scene="验证提取", model=model_id, prompt_summary=prompt_text,
                         error=str(exc), success=False, elapsed_s=elapsed_s)
        return {"success": False, "image_file": image_path.name, "extraction_output": "", "error": str(exc), "elapsed": "0.0"}


def read_factors_script(paths: Any, work_dir: str) -> list[dict[str, Any]]:
    factors_path = None
    for name in ("factors.xlsx", "factors.xls", "factors.csv"):
        candidate = Path(work_dir) / name
        if candidate.exists():
            factors_path = candidate
            break
    if factors_path is None:
        return []
    script = paths.skills_dir / "doc-extract-prompt-gen" / "read_factors.py"
    output = subprocess.run(
        [sys.executable, str(script), str(factors_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if output.returncode != 0:
        raise ValueError(output.stderr.strip() or output.stdout.strip() or "failed to read factors")
    return json.loads(output.stdout or "[]")


def resolve_factors_workbook_path(work_dir: str) -> Path:
    return Path(work_dir) / "factors.xlsx"


def run_factor_json(paths: Any, work_dir: str, group_size: int = 4, materials: Optional[list[str]] = None) -> list[dict[str, Any]]:
    script = paths.skills_dir / "factor-json-generator" / "generate_factor_json.py"
    cmd = [sys.executable, str(script), work_dir, "--group-size", str(group_size)]
    if materials:
        cmd.extend(["--materials"] + materials)
    output = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if output.returncode != 0:
        raise ValueError(output.stderr.strip() or output.stdout.strip() or "factor json generation failed")
    for line in output.stdout.splitlines():
        if line.startswith("RESULTS_JSON:"):
            return json.loads(line.split("RESULTS_JSON:", 1)[1])
    return []


def run_generate_prompt(
    paths: Any,
    settings: dict[str, Any],
    work_dir: str,
    material_name: Optional[str],
    model_cfg_id: Optional[str] = None,
    use_case_library: bool = True,
    rule_profile_id: Optional[str] = None,
    task_store: Optional[TaskStore] = None,
    task_id: Optional[str] = None,
) -> dict[str, Any]:
    material_dir = Path(work_dir) / material_name if material_name else Path(work_dir)
    user_id = _resolve_user_id_from_work_dir(paths, work_dir)
    script = paths.skills_dir / "doc-extract-prompt-gen" / "generate_prompt.py"
    model_config = resolve_model_config(settings, model_cfg_id)
    extract_profile = resolve_extract_profile(settings, rule_profile_id)
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": model_config["api_key"],
        "OPENAI_API_KEY": model_config["api_key"],
        "OPENAI_BASE_URL": model_config["base_url"],
        "MODEL_NAME": model_config["model"],
        "GENERATE_EXTRA_PARAMS": json.dumps(model_config["params"], ensure_ascii=False),
        "LLM_TIMEOUT": str(settings.get("llm_timeout", 120)),
        "EXTRACT_GOD_PROMPT": extract_profile["systemPrompt"],
        "GENERATE_USE_CASE_LIBRARY": "1" if use_case_library else "0",
        "GENERATE_RULE_PROFILE_JSON": json.dumps(extract_profile, ensure_ascii=False),
        "AUTO_PROMPT_SKILLS_DIR": str(paths.skills_dir),
        "AUTO_PROMPT_API_URL": f"http://127.0.0.1:{os.environ.get('PORT', '18765')}",
        "AUTO_PROMPT_API_TOKEN": settings.get("api_token", ""),
    }
    args = [sys.executable, str(script), str(material_dir)]
    if material_name:
        args.append(material_name)
    if task_store and task_id:
        run_lines_cancellable(args, env, None, task_store, task_id)
    else:
        output = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env)
        if output.returncode != 0:
            raise ValueError(output.stderr.strip() or output.stdout.strip() or "generate prompt failed")
    raw_output = material_dir / f"{material_dir.name}--要素提取完整提示词.txt"
    raw_artifact = material_dir / f"{material_dir.name}--要素提示词.json"
    preview_prompt = ""
    artifact: Optional[dict[str, Any]] = None
    if raw_artifact.exists():
        artifact = load_factor_prompt_artifact(raw_artifact)
        preview_prompt = raw_output.read_text(encoding="utf-8") if raw_output.exists() else build_preview_prompt(
            artifact.get("template", {}).get("prompt_template", ""),
            artifact.get("factors", []),
        )
    elif raw_output.exists():
        preview_prompt = raw_output.read_text(encoding="utf-8")
    if not preview_prompt.strip():
        raise ValueError(f"generated prompt is empty: {raw_output}")
    prompts_dir = paths.user_output_root / user_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\u4e00-\u9fff-]", "_", material_dir.name)
    output_file = prompts_dir / f"{safe_name}--要素提取完整提示词.txt"
    output_file.write_text(preview_prompt, encoding="utf-8")
    artifact_file = ""
    if artifact is not None:
        save_factor_prompt_artifact(raw_artifact, artifact)
        artifact_file = str(raw_artifact)
    return {
        "output_file": str(output_file),
        "artifact_file": artifact_file,
        "factors_count": len(read_factors_script(paths, str(material_dir))),
        "images_count": sum(1 for entry in material_dir.iterdir() if entry.is_file() and entry.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".pdf"}),
        "prompt_template": preview_prompt,
        "preview_prompt": preview_prompt,
        "artifact": artifact,
    }


def validate_factors_for_generate(paths: Any, work_dir: str, selected_materials: Optional[list[str]] = None) -> dict[str, Any]:
    return validate_workspace_bundle(paths, work_dir, selected_materials)


def validate_review_rule_workspace(paths: Any, work_dir: str) -> dict[str, Any]:
    return validate_workspace_bundle(paths, work_dir)


def _resolve_user_id_from_work_dir(paths: Any, work_dir: str) -> str:
    """
    从已解析的绝对路径 work_dir 中提取 user_id。
    work_dir 格式: /.../workspaces/{user_id}/my-project
    """
    ws_root = str(paths.user_workspace_root)  # /.../workspaces
    if work_dir.startswith(ws_root):
        rel = work_dir[len(ws_root):].lstrip("/")
        first = rel.split("/")[0] if rel else ""
        if first:
            return first
    return "default"


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=1)
        return
    except Exception:
        pass
    try:
        process.kill()
        process.wait(timeout=1)
    except Exception:
        pass


def run_lines(command: list[str], env: dict[str, str], cwd: Optional[str], log_cb: Optional[Any] = None) -> list[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    lines: list[str] = []
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip("\r\n")
        lines.append(line)
        if log_cb and line and not line.startswith("RESULTS_JSON:") and not line.startswith("TEST_RESULT_JSON:"):
            log_cb(line)
    if process.wait() != 0:
        raise ValueError(lines[-1] if lines else "python task failed")
    return lines


def run_lines_cancellable(
    command: list[str],
    env: dict[str, str],
    cwd: Optional[str],
    task_store: TaskStore,
    task_id: str,
    log_cb: Optional[Any] = None,
) -> list[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    task_store.register_process(task_id, process)
    lines: list[str] = []
    stdout = process.stdout
    assert stdout is not None
    try:
        while True:
            if task_store.is_cancel_requested(task_id):
                _terminate_process(process)
                raise TaskCancelledError("已停止生成")

            if process.poll() is not None:
                break

            ready, _, _ = select.select([stdout], [], [], 0.2)
            if not ready:
                continue

            raw_line = stdout.readline()
            if not raw_line:
                continue
            line = raw_line.rstrip("\r\n")
            lines.append(line)
            if log_cb and line and not line.startswith("RESULTS_JSON:") and not line.startswith("TEST_RESULT_JSON:"):
                log_cb(line)

        for raw_line in stdout.readlines():
            line = raw_line.rstrip("\r\n")
            lines.append(line)
            if log_cb and line and not line.startswith("RESULTS_JSON:") and not line.startswith("TEST_RESULT_JSON:"):
                log_cb(line)

        if task_store.is_cancel_requested(task_id):
            raise TaskCancelledError("已停止生成")

        if process.wait() != 0:
            raise ValueError(lines[-1] if lines else "python task failed")
        return lines
    finally:
        try:
            stdout.close()
        except Exception:
            pass
        task_store.unregister_process(task_id, process)


def run_classify(
    paths: Any,
    settings: dict[str, Any],
    work_dir: str,
    max_rounds: int,
    model_cfg_id: Optional[str] = None,
    log_cb: Optional[Any] = None,
) -> dict[str, Any]:
    script = paths.skills_dir / "material-classifier" / "classify_materials.py"
    report_path = Path(work_dir) / "classification_report.json"
    if report_path.exists():
        report_path.unlink()
    model_config = resolve_model_config(settings, model_cfg_id)
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": model_config["api_key"],
        "OPENAI_API_KEY": model_config["api_key"],
        "OPENAI_BASE_URL": model_config["base_url"],
        "CLASSIFY_MODEL_NAME": model_config["model"],
        "CLASSIFY_EXTRA_PARAMS": json.dumps(model_config["params"], ensure_ascii=False),
        "CLASSIFY_GOD_PROMPT": settings["god_prompt"],
    }
    run_lines([sys.executable, str(script), work_dir, str(max_rounds)], env, work_dir, log_cb)
    if not report_path.exists():
        raise ValueError("classification report not generated")
    return load_json(report_path, {})


def validate_classify_workspace(paths: Any, work_dir: str) -> dict[str, Any]:
    return validate_workspace_bundle(paths, work_dir)


def run_test_classify(
    paths: Any,
    settings: dict[str, Any],
    work_dir: str,
    prompt_type: str,
    prompt_content: str,
    model_cfg_id: Optional[str] = None,
    log_cb: Optional[Any] = None,
) -> dict[str, Any]:
    script = paths.skills_dir / "material-classifier" / "classify_materials.py"
    prompt_path = Path(work_dir) / f".test_prompt_{prompt_type}.txt"
    prompt_path.write_text(prompt_content, encoding="utf-8")
    model_config = resolve_model_config(settings, model_cfg_id)
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": model_config["api_key"],
        "OPENAI_API_KEY": model_config["api_key"],
        "OPENAI_BASE_URL": model_config["base_url"],
        "CLASSIFY_MODEL_NAME": model_config["model"],
        "CLASSIFY_EXTRA_PARAMS": json.dumps(model_config["params"], ensure_ascii=False),
    }
    try:
        lines = run_lines([sys.executable, str(script), f"--test-prompt={prompt_type}", f"--prompt-file={prompt_path}", work_dir], env, work_dir, log_cb)
    finally:
        prompt_path.unlink(missing_ok=True)
    for line in lines:
        if line.startswith("TEST_RESULT_JSON:"):
            return json.loads(line.split("TEST_RESULT_JSON:", 1)[1])
    raise ValueError("test result not found")


def run_review_rule(
    paths: Any,
    settings: dict[str, Any],
    work_dir: str,
    use_llm: bool,
    log_cb: Optional[Any] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    model_cfg_id: Optional[str] = None,
    materials: Optional[list[str]] = None,
    task_store: Optional[TaskStore] = None,
    task_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    script = paths.skills_dir / "review-rule-generator" / "generate_review_rule.py"
    cmd = [sys.executable, str(script), work_dir]
    model_config = resolve_model_config(settings, model_cfg_id)
    if use_llm:
        resolved_api_key = model_config["api_key"] if model_cfg_id else (api_key if api_key is not None else model_config["api_key"])
        resolved_base_url = model_config["base_url"] if model_cfg_id else (base_url or model_config["base_url"])
        resolved_model = model_config["model"] if model_cfg_id else (model or model_config["model"])
        resolved_timeout = str(settings.get("llm_timeout", 120))
        cmd.extend([
            "--use-llm",
            "--api-key",
            resolved_api_key,
            "--base-url",
            resolved_base_url,
            "--model",
            resolved_model,
            "--timeout",
            resolved_timeout,
        ])
    if materials:
        cmd.extend(["--materials"] + materials)
    env = os.environ.copy()
    env["AUTO_PROMPT_API_URL"] = f"http://127.0.0.1:{os.environ.get('PORT', '18765')}"
    env["AUTO_PROMPT_API_TOKEN"] = settings.get("api_token", "")
    env["GENERATE_EXTRA_PARAMS"] = json.dumps(model_config["params"], ensure_ascii=False)
    env["REVIEW_RULE_BUILTIN_VARIABLES"] = json.dumps(
        normalize_review_rule_builtin_variables(settings.get("review_rule_builtin_variables")),
        ensure_ascii=False,
    )
    if task_store and task_id:
        lines = run_lines_cancellable(cmd, env, None, task_store, task_id, log_cb)
    else:
        lines = run_lines(cmd, env, None, log_cb)
    for line in lines:
        if line.startswith("RESULTS_JSON:"):
            return json.loads(line.split("RESULTS_JSON:", 1)[1])
    return []


def _resolve_user_work_dir(paths: Any, work_dir: str, user_id: str) -> str:
    """
    将前端传入的 workDir 转换为真实文件系统路径。

    前端传入的 workDir 可能是：
    - 完整路径：.runtime-data/workspaces/{workspace_id}/xxx
    - 相对路径：workspaces/{user_id}/xxx
    - 用户相对路径：xxx（不带前缀）

    统一映射到：workspaces/{user_id}/xxx
    """
    if not work_dir:
        return str(paths.user_workspace_root / user_id)

    workspace_root = paths.user_workspace_root.resolve()

    def resolve_workspace_path(candidate: Path) -> str:
        resolved = candidate.expanduser().resolve(strict=False)
        try:
            relative = resolved.relative_to(workspace_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid workspace path") from exc

        if relative.parts and relative.parts[0] != user_id:
            raise HTTPException(status_code=403, detail="workspace access denied")

        return str(resolved)

    # 兼容前端恢复的绝对路径工作区
    if Path(work_dir).is_absolute():
        return resolve_workspace_path(Path(work_dir))

    # 如果是 .runtime-data/workspaces 格式，直接返回完整路径
    if work_dir.startswith(".runtime-data/workspaces/"):
        return resolve_workspace_path(paths.repo_root / work_dir)

    # 去掉 "workspaces" 前缀
    rel = work_dir
    if rel.startswith("workspaces/"):
        rel = rel[len("workspaces/"):]
    elif rel == "workspaces":
        rel = ""

    # 如果去掉前缀后第一个部分不是 user_id，说明是旧格式或相对路径，加前缀
    first = rel.split("/")[0] if rel else ""
    if first != user_id:
        rel = f"{user_id}/{rel}" if rel else user_id

    # 去掉可能的重复 user_id（处理 "userA/userA/xxx" 的边界情况）
    if rel.startswith(f"{user_id}/{user_id}/"):
        rel = rel[len(f"{user_id}/"):]

    return str(paths.user_workspace_root / rel)


def _resolve_user_file_path(paths: Any, file_path: str, user_id: str) -> Path:
    if not file_path:
        raise HTTPException(status_code=400, detail="missing file path")

    target = Path(file_path)
    if not target.is_absolute():
        target = paths.repo_root / target

    resolved = target.expanduser().resolve(strict=False)
    allowed_roots = [
        (paths.user_workspace_root / user_id).resolve(),
        (paths.user_output_root / user_id).resolve(),
    ]

    for allowed_root in allowed_roots:
        try:
            resolved.relative_to(allowed_root)
            return resolved
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="file access denied")


def build_zip_archive(file_paths: list[Path]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            zip_file.writestr(file_path.name, file_path.read_bytes())
    return buffer.getvalue()


def _download_no_cache_headers(extra_headers: Optional[dict[str, str]] = None) -> dict[str, str]:
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_zip_from_directory(root_dir: Path) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        for item in sorted(root_dir.rglob("*")):
            if item.is_file():
                arcname = item.relative_to(root_dir.parent)
                zip_file.writestr(str(arcname), item.read_bytes())
    return buffer.getvalue()


def build_zip_from_workdir(work_dir: Path, classified_dir: Path) -> bytes:
    """分类结果下载包：已分类材料 + 关键产物文件"""
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        # 1) 已分类材料目录
        for item in sorted(classified_dir.rglob("*")):
            if item.is_file():
                arcname = item.relative_to(work_dir)
                zip_file.writestr(str(arcname), item.read_bytes())

        # 2) 分类关键结果文件（若存在）
        optional_files = [
            "最新分类信息提取提示词.txt",
            "最新分类附件归集提示词.txt",
            "分类信息提取提示词模板.txt",
            "分类附件归集提示词模板.txt",
            "classification_report.json",
        ]
        for name in optional_files:
            file_path = work_dir / name
            if file_path.exists() and file_path.is_file():
                zip_file.writestr(name, file_path.read_bytes())

    return buffer.getvalue()


def collect_workspace_artifact_files(work_dir: Path, patterns: list[str]) -> list[Path]:
    found: dict[Path, Path] = {}
    for pattern in patterns:
        for candidate in work_dir.rglob(pattern):
            if candidate.is_file():
                found[candidate] = candidate
    return sorted(found.values())


def build_zip_from_file_set(root_dir: Path, file_paths: list[Path]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            arcname = file_path.relative_to(root_dir)
            zip_file.writestr(str(arcname), file_path.read_bytes())
    return buffer.getvalue()


def _ensure_user_dirs(paths: Any, user_id: str) -> None:
    """确保用户隔离目录存在"""
    (paths.user_workspace_root / user_id).mkdir(parents=True, exist_ok=True)
    (paths.user_output_root / user_id / "prompts").mkdir(parents=True, exist_ok=True)
    (paths.user_output_root / user_id / "review_rules").mkdir(parents=True, exist_ok=True)


def load_case_library(paths: Any, data_store: Any) -> dict[str, Any]:
    """所有案例（全员可见）"""
    return {"version": "1.0", "cases": data_store.list_cases()}


def save_case_library(paths: Any, data_store: Any, value: dict[str, Any]) -> None:
    """保存案例（写入 admin 名下）"""
    cases = value.get("cases", [])
    data_store.import_cases(cases, overwrite=True)


def load_review_rule_library_file(paths: Any, data_store: Any) -> list[Any]:
    """所有审查规则（全员可见）"""
    return data_store.list_review_rules()


def save_review_rule_library_file(paths: Any, data_store: Any, value: list[Any]) -> None:
    """保存审查规则（写入 admin 名下）"""
    data_store.save_review_rules(value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths = get_paths()
    data_store = DataStore(paths.app_db_path)
    app.state.paths = paths
    app.state.auth = AuthStore(paths.app_db_path)
    app.state.tasks = TaskStore(paths.task_root)
    app.state.workspaces = WorkspaceService(paths)
    app.state.ui_settings = UiSettingsStore(paths.settings_path, paths.repo_root / "auto-prompt.project.json")
    app.state.data = data_store
    app.state.llm_logs = LlmLogStore()
    yield


app = FastAPI(title="Auto Prompt API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def current_user(request: Request) -> Any:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else auth
    if not token:
        token = request.query_params.get("authToken", "")
    if not token:
        fail(401, "missing auth token")
    user = request.app.state.auth.get_user_from_token(token)
    if not user:
        fail(401, "invalid or expired session")
    return user


def current_admin(user: Any = Depends(current_user)) -> Any:
    if getattr(user.role, "value", user.role) != "admin":
        fail(403, "admin access required")
    return user


@app.post("/api/auth/login")
async def login(body: LoginRequest, request: Request):
    user = request.app.state.auth.authenticate(body.username, body.password)
    if user is None:
        fail(401, "invalid username or password")
    session = request.app.state.auth.create_session(user, remember_me=body.rememberMe)
    return {"token": session["token"], "expiresAt": session["expires_at"], "user": user_to_json(user)}


@app.get("/api/auth/me")
async def me(user: Any = Depends(current_user)):
    return user_to_json(user)


@app.post("/api/auth/logout")
async def logout(request: Request, user: Any = Depends(current_user)):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else auth
    request.app.state.auth.delete_session(token)
    return {"ok": True}


@app.get("/api/users")
async def users(request: Request, admin: Any = Depends(current_admin)):
    return [user_to_json(user) for user in request.app.state.auth.list_users()]


@app.post("/api/users")
async def create_user(body: CreateUserRequest, request: Request, admin: Any = Depends(current_admin)):
    try:
        return user_to_json(request.app.state.auth.create_user(body))
    except ValueError as exc:
        fail(400, str(exc))


@app.post("/api/users/{user_id}/password")
async def reset_password(user_id: str, body: ResetPasswordRequest, request: Request, admin: Any = Depends(current_admin)):
    if not request.app.state.auth.reset_password(user_id, body.password):
        fail(404, "user not found")
    return {"ok": True}


@app.put("/api/users/{user_id}/status")
async def update_status(user_id: str, body: UpdateUserStatusRequest, request: Request, admin: Any = Depends(current_admin)):
    if not request.app.state.auth.update_user_status(user_id, body.active):
        fail(404, "user not found")
    return {"ok": True}


@app.get("/api/settings")
async def get_settings(request: Request, user: Any = Depends(current_user)):
    return request.app.state.ui_settings.load_front()


@app.put("/api/settings")
async def put_settings(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    request.app.state.ui_settings.save_front(payload)
    return {"ok": True}


@app.get("/api/settings/default-prompts")
async def default_prompts(request: Request, user: Any = Depends(current_user)):
    return request.app.state.ui_settings.default_god_prompts()


@app.get("/api/god-prompts")
async def list_god_prompts(request: Request, user: Any = Depends(current_user)):
    """所有 god prompts（全员可见）"""
    return request.app.state.data.list_god_prompts()


@app.put("/api/god-prompts")
async def save_god_prompts(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    """批量保存 god prompts（仅 admin 可写）"""
    prompts = payload.get("prompts", {})
    for name, content in prompts.items():
        request.app.state.data.save_god_prompt(str(name), str(content))
    return {"ok": True}


@app.post("/api/settings/test-key")
async def test_key(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    try:
        request.app.state.ui_settings.test_api_key(payload.get("apiKey", ""))
    except ValueError as exc:
        fail(400, str(exc))
    return {"ok": True}


@app.post("/api/settings/test-model")
async def test_model(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    settings = request.app.state.ui_settings.load_front()
    try:
        result = test_model_connection(
            payload.get("model") or {},
            fallback_api_key=payload.get("fallbackApiKey") or settings.get("api_key", ""),
            timeout=int(payload.get("timeout") or settings.get("llm_timeout", 30)),
        )
    except ValueError as exc:
        fail(400, str(exc))
    except Exception as exc:
        fail(400, str(exc))
    return result


@app.post("/api/workspaces")
async def create_workspace_route(
    request: Request,
    name: Optional[str] = Form(default=None),
    manifest: Optional[str] = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    user: Any = Depends(current_user),
):
    manifest_items = json.loads(manifest or "[]")
    uploads = []
    for index, file in enumerate(files):
        relative = file.filename or "upload.bin"
        if index < len(manifest_items) and isinstance(manifest_items[index], dict):
            relative = manifest_items[index].get("relativePath") or relative
        uploads.append(UploadedBlob(original_name=file.filename or relative, relative_path=relative, content=await file.read()))
    return workspace_to_json(request.app.state.workspaces.create_workspace(user.id, name=name, uploads=uploads))


@app.post("/api/uploads")
async def upload_files_route(request: Request, manifest: Optional[str] = Form(default=None), files: list[UploadFile] = File(default=[]), user: Any = Depends(current_user)):
    manifest_items = json.loads(manifest or "[]")
    uploads = []
    for index, file in enumerate(files):
        relative = file.filename or "upload.bin"
        if index < len(manifest_items) and isinstance(manifest_items[index], dict):
            relative = manifest_items[index].get("relativePath") or relative
        uploads.append(UploadedBlob(original_name=file.filename or relative, relative_path=relative, content=await file.read()))
    return {"paths": request.app.state.workspaces.save_temp_uploads(user.id, uploads)}


@app.post("/api/workspaces/upload")
async def workspace_upload_legacy(request: Request, files: list[UploadFile] = File(default=[]), user: Any = Depends(current_user)):
    uploads = [UploadedBlob(original_name=file.filename or "upload.bin", relative_path=file.filename or "upload.bin", content=await file.read()) for file in files]
    summary = request.app.state.workspaces.create_workspace(user.id, uploads=uploads)
    return {"data": {"id": summary.id, "path": summary.root_path, "rootPath": summary.root_path}}


@app.get("/api/workspaces/list")
async def list_workspaces_route(request: Request, module: Optional[str] = Query(default=None), user: Any = Depends(current_user)):
    return request.app.state.workspaces.list_workspaces(user.id, module=module)


@app.put("/api/workspaces/{workspace_id}/module")
async def tag_workspace_route(workspace_id: str, payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    module = payload.get("module", "")
    if not request.app.state.workspaces.tag_workspace(user.id, workspace_id, module):
        fail(404, "workspace not found")
    return {"ok": True}


@app.put("/api/workspaces/activity")
async def update_workspace_activity_route(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    work_dir = payload.get("workDir", "")
    module = payload.get("module")
    status = payload.get("status")
    paths = request.app.state.paths
    real_work_dir = Path(_resolve_user_work_dir(paths, work_dir, user.id))
    workspace_id = real_work_dir.name
    if not request.app.state.workspaces.update_workspace_activity(
        user.id,
        workspace_id,
        module=module,
        status=status,
    ):
        fail(404, "workspace not found")
    return {"ok": True}


@app.delete("/api/workspaces/{workspace_id}")
async def delete_workspace_route(workspace_id: str, request: Request, user: Any = Depends(current_user)):
    if not request.app.state.workspaces.delete_workspace(user.id, workspace_id):
        fail(404, "workspace not found")
    return {"ok": True}


@app.get("/api/workspaces/materials")
async def workspace_materials(workDir: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, workDir, user.id)
    result = [
        {"name": item["name"], "path": item["path"], "image_count": item["image_count"]}
        for item in collect_workspace_material_dirs(Path(real_dir))
    ]
    return {"data": result}


@app.get("/api/workspaces/factors")
async def workspace_factors(request: Request, workDir: str = Query(...), user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, workDir, user.id)
    return {"data": read_factors_script(paths, real_dir)}


@app.get("/api/workspaces/factors-workbook")
async def workspace_factors_workbook(request: Request, workDir: str = Query(...), user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, workDir, user.id)
    workbook_path = resolve_factors_workbook_path(real_dir)
    return {"data": load_factors_workbook(workbook_path)}


@app.put("/api/workspaces/factors-workbook")
async def update_workspace_factors_workbook(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    workbook_path = resolve_factors_workbook_path(real_dir)
    workbook_data = save_factors_workbook(
        workbook_path,
        payload.get("headers") or [],
        payload.get("rows") or [],
        payload.get("mergedRanges") or [],
    )
    validation = validate_workspace_bundle(paths, real_dir)
    return {"ok": True, "data": {"workbook": workbook_data, "validation": validation}}


@app.post("/api/workspaces/factors-workbook/repair-suggestions")
async def workspace_factors_workbook_repair_suggestions(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    settings = request.app.state.ui_settings.load_front()
    builtin_variables = normalize_review_rule_builtin_variables(settings.get("review_rule_builtin_variables"))
    use_llm = bool(payload.get("useLlm", True))
    model_cfg_id = payload.get("modelCfgId")

    async def llm_suggester(context: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(
            suggest_review_rule_description_with_model,
            settings,
            model_cfg_id,
            context,
        )

    result = await generate_factors_repair_suggestions(
        headers=payload.get("headers") or [],
        rows=payload.get("rows") or [],
        merged_ranges=payload.get("mergedRanges") or [],
        diagnostics=payload.get("diagnostics") or [],
        builtin_variables=builtin_variables,
        workspace_materials=collect_workspace_material_dirs(Path(real_dir)),
        llm_rule_description_suggester=llm_suggester if use_llm else None,
    )
    return {"ok": True, "data": result}


@app.post("/api/workspaces/factors-workbook/apply-repair-suggestion")
async def apply_workspace_factors_workbook_repair_suggestion(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    try:
        applied = apply_factors_repair_suggestion_patches(
            work_dir=real_dir,
            patches=payload.get("patches") or [],
        )
    except ValueError as exc:
        fail(400, str(exc))
    validation = validate_workspace_bundle(paths, real_dir)
    return {"ok": True, "data": {"applied": applied, "validation": validation}}


@app.put("/api/workspaces/gen-status")
async def update_gen_status(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    work_dir = payload.get("workDir", "")
    status = payload.get("status", "")  # "generating" | "done" | "error" | ""
    paths = request.app.state.paths
    real_work_dir = Path(_resolve_user_work_dir(paths, work_dir, user.id))
    status_file = real_work_dir / ".gen_status"
    if status:
        status_file.write_text(status)
    elif status_file.exists():
        status_file.unlink()
    return {"ok": True}


@app.get("/api/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, request: Request, user: Any = Depends(current_user)):
    return workspace_to_json(request.app.state.workspaces.get_workspace(user.id, workspace_id))


@app.post("/api/classify/validate-workdir")
async def classify_validate_workdir(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    result = validate_classify_workspace(paths, real_work_dir)
    return {"data": result}


@app.get("/api/classify/download-result")
async def classify_download_result(workDir: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = Path(_resolve_user_work_dir(paths, workDir, user.id))
    artifact_files = collect_workspace_artifact_files(
        real_work_dir,
        [
            "材料分类提示词.json",
            "材料分类完整提示词.txt",
            "最新分类信息提取提示词.txt",
            "最新分类附件归集提示词.txt",
            "classification_report.json",
        ],
    )
    if not artifact_files:
        raise HTTPException(status_code=404, detail="未找到可下载的分类提示词结果")
    factors_file = resolve_factors_workbook_path(str(real_work_dir))
    if factors_file.exists():
        artifact_files.append(factors_file)

    archive = build_zip_from_file_set(real_work_dir, artifact_files)
    filename = f"材料分类结果_{real_work_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers=_download_no_cache_headers(
            {
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            }
        ),
    )


@app.get("/api/generate/download-result")
async def generate_download_result(workDir: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = Path(_resolve_user_work_dir(paths, workDir, user.id))
    artifact_files = collect_workspace_artifact_files(
        real_work_dir,
        [
            "*--要素提取完整提示词.txt",
            "*--要素提示词.json",
            "*--要素信息录入.json",
        ],
    )
    if not artifact_files:
        raise HTTPException(status_code=404, detail="未找到可下载的要素生成结果")
    factors_file = resolve_factors_workbook_path(str(real_work_dir))
    if factors_file.exists():
        artifact_files.append(factors_file)

    archive = build_zip_from_file_set(real_work_dir, artifact_files)
    filename = f"要素生成结果_{real_work_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers=_download_no_cache_headers(
            {
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            }
        ),
    )


@app.get("/api/review-rule/download-result")
async def review_rule_download_result(workDir: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = Path(_resolve_user_work_dir(paths, workDir, user.id))
    artifact_files = collect_workspace_artifact_files(
        real_work_dir,
        [
            "*--审查规则导入.json",
        ],
    )
    if not artifact_files:
        raise HTTPException(status_code=404, detail="未找到可下载的审查规则结果")
    factors_file = resolve_factors_workbook_path(str(real_work_dir))
    if factors_file.exists():
        artifact_files.append(factors_file)

    archive = build_zip_from_file_set(real_work_dir, artifact_files)
    filename = f"审查规则结果_{real_work_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers=_download_no_cache_headers(
            {
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            }
        ),
    )


@app.post("/api/generate/prompt")
async def generate_prompt(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    settings = request.app.state.ui_settings.load_front()
    paths = request.app.state.paths
    _ensure_user_dirs(paths, user.id)
    real_work_dir = _resolve_user_work_dir(paths, payload["workDir"], user.id)
    validation = validate_workspace_bundle(paths, real_work_dir, [payload.get("materialName")] if payload.get("materialName") else None)
    if not validation.get("ok"):
        fail(400, "\n".join(validation.get("errors", [])) or "workspace validation failed")
    llm_logs = request.app.state.llm_logs
    start = time.time()
    model_cfg_id = payload.get("modelCfgId")
    model_id = resolve_model_id(settings, model_cfg_id)
    try:
        data = run_generate_prompt(
            paths,
            settings,
            real_work_dir,
            payload.get("materialName"),
            model_cfg_id=model_cfg_id,
            use_case_library=bool(payload.get("useCaseLibrary", True)),
            rule_profile_id=payload.get("ruleProfileId"),
        )
        llm_logs.add(scene="提示词生成", model=model_id,
                     prompt_summary=f"材料: {payload.get('materialName', '全部')}", 
                     response_summary=data.get("prompt_template", "")[:500],
                     success=True, elapsed_s=time.time() - start)
    except ValueError as exc:
        llm_logs.add(scene="提示词生成", model=model_id,
                     prompt_summary=f"材料: {payload.get('materialName', '全部')}",
                     error=str(exc), success=False, elapsed_s=time.time() - start)
        fail(400, str(exc))
    return {"data": data}


@app.post("/api/generate/validate-factors")
async def validate_generate_factors(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    selected_materials = payload.get("materials") or []
    result = validate_factors_for_generate(paths, real_work_dir, selected_materials)
    return {"data": result}


@app.post("/api/review-rule/validate-workspace")
async def validate_review_rule_workspace_route(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
    return {"data": validate_review_rule_workspace(paths, real_work_dir)}


@app.post("/api/generate/verify")
async def generate_verify(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    settings = request.app.state.ui_settings.load_front()
    paths = request.app.state.paths
    # materialDir 可能是前端传回的后端返回的路径（已包含 workspaces/{user_id}/...）
    # 或者是用户编辑后的路径；直接使用（不做二次映射避免路径错误）
    material_dir = Path(payload["materialDir"])
    prompt_text = payload.get("promptText", "")
    if payload.get("artifactFile"):
        artifact = load_factor_prompt_artifact(Path(payload["artifactFile"]))
        prompt_text = build_preview_prompt(artifact.get("template", {}).get("prompt_template", ""), artifact.get("factors", []))
    elif isinstance(payload.get("artifact"), dict):
        artifact = payload["artifact"]
        prompt_text = build_preview_prompt(
            artifact.get("template", {}).get("prompt_template", ""),
            artifact.get("factors", []),
        )
    model_cfg_id = payload.get("modelCfgId")
    model_config = resolve_model_config(settings, model_cfg_id)
    result = run_verify_extraction(material_dir, prompt_text, model_config["model"], model_config["api_key"],
                                   base_url=model_config["base_url"],
                                   extra_params=model_config["params"],
                                   llm_logs=request.app.state.llm_logs)
    if not result["success"]:
        fail(400, result["error"])
    return {"data": result}


@app.post("/api/generate/save-prompt")
async def save_prompt(body: SavePromptRequest, user: Any = Depends(current_user)):
    target = Path(body.filePath)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content, encoding="utf-8")
    return {"ok": True}


@app.post("/api/generate/save-artifact")
async def save_artifact(body: SaveArtifactRequest, user: Any = Depends(current_user)):
    artifact = save_factor_prompt_artifact(body.filePath, body.artifact)
    if body.previewFilePath:
        preview_target = Path(body.previewFilePath)
        preview_target.parent.mkdir(parents=True, exist_ok=True)
        preview_target.write_text(
            build_preview_prompt(
                artifact.get("template", {}).get("prompt_template", ""),
                artifact.get("factors", []),
            ),
            encoding="utf-8",
        )
    return {"ok": True, "data": {"artifact": artifact}}


@app.post("/api/generate/factor-json")
async def generate_factor_json(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_work_dir = _resolve_user_work_dir(paths, payload["workDir"], user.id)
    group_size = int(payload.get("groupSize") or 4)
    materials = payload.get("materials") or None
    return {"data": run_factor_json(paths, real_work_dir, group_size=group_size, materials=materials)}


@app.get("/api/files/read")
async def read_file(path: str = Query(...), user: Any = Depends(current_user)):
    return {"data": {"content": Path(path).read_text(encoding="utf-8")}}


@app.get("/api/files/content")
async def file_content(path: str = Query(...), user: Any = Depends(current_user)):
    return {"content": Path(path).read_text(encoding="utf-8")}


@app.put("/api/files/content")
async def put_file_content(payload: dict[str, Any], user: Any = Depends(current_user)):
    target = Path(payload["path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload["content"], encoding="utf-8")
    return {"ok": True}


@app.get("/api/files/download")
async def download_file(path: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    target = _resolve_user_file_path(request.app.state.paths, path, user.id)
    media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        target,
        media_type=media_type or "application/octet-stream",
        filename=target.name,
        headers=_download_no_cache_headers(),
    )


@app.get("/api/files/download-batch")
async def download_batch_files(pathsJson: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    try:
        requested_paths = json.loads(pathsJson)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid paths json") from exc

    if not isinstance(requested_paths, list) or not requested_paths:
        raise HTTPException(status_code=400, detail="no files requested")

    file_paths = []
    for raw_path in requested_paths:
        if not isinstance(raw_path, str):
            raise HTTPException(status_code=400, detail="invalid file path")
        target = _resolve_user_file_path(request.app.state.paths, raw_path, user.id)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail=f"file not found: {target.name}")
        file_paths.append(target)

    archive = build_zip_archive(file_paths)
    filename = f"要素JSON_批量下载_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers=_download_no_cache_headers(
            {
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            }
        ),
    )


@app.post("/api/files/open-location")
async def open_location(payload: dict[str, Any], user: Any = Depends(current_user)):
    return {"ok": True}


@app.get("/api/browse")
async def browse(path: str = Query(...), user: Any = Depends(current_user)):
    target = Path(path)
    if target.is_file():
        media_type, _ = mimetypes.guess_type(str(target))
        return FileResponse(target, media_type=media_type or "application/octet-stream", filename=target.name)
    items = [f"<li>{entry.name}</li>" for entry in sorted(target.iterdir(), key=lambda item: item.name.lower())]
    return HTMLResponse(f"<html><body><h1>{target}</h1><ul>{''.join(items)}</ul></body></html>")


@app.post("/api/tasks/{kind}")
async def start_task(kind: str, payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    task = request.app.state.tasks.create(kind.replace("-", "_"), user.id, request.app.state.data)
    request.app.state.tasks.mark_running(task.id, 5)

    def worker() -> None:
        llm_logs = request.app.state.llm_logs
        try:
            settings = request.app.state.ui_settings.load_front()
            paths = request.app.state.paths
            _ensure_user_dirs(paths, user.id)
            real_work_dir = _resolve_user_work_dir(paths, payload.get("workDir", ""), user.id)
            if kind == "generate":
                validation = validate_workspace_bundle(paths, real_work_dir, [payload.get("materialName")] if payload.get("materialName") else None)
                for warning in validation.get("warnings", []):
                    request.app.state.tasks.append_log(task.id, f"[校验提示] {warning}")
                if not validation.get("ok"):
                    for error in validation.get("errors", []):
                        request.app.state.tasks.append_log(task.id, f"[校验失败] {error}")
                    raise ValueError("\n".join(validation.get("errors", [])) or "generate workspace validation failed")
                t0 = time.time()
                model_cfg_id = payload.get("modelCfgId")
                model_id = resolve_model_id(settings, model_cfg_id)
                result = run_generate_prompt(
                    paths,
                    settings,
                    real_work_dir,
                    payload.get("materialName"),
                    model_cfg_id=model_cfg_id,
                    use_case_library=bool(payload.get("useCaseLibrary", True)),
                    rule_profile_id=payload.get("ruleProfileId"),
                    task_store=request.app.state.tasks,
                    task_id=task.id,
                )
                llm_logs.add(scene="提示词生成", model=model_id,
                             prompt_summary=f"材料: {payload.get('materialName', '全部')}",
                             response_summary=result.get("prompt_template", "")[:500],
                             success=True, elapsed_s=time.time() - t0)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "verify-extraction":
                material_dir = Path(payload["materialDir"])
                prompt_text = payload.get("promptText", "")
                model_cfg_id = payload.get("modelCfgId")
                model_config = resolve_model_config(settings, model_cfg_id)
                result = run_verify_extraction(material_dir, prompt_text, model_config["model"], model_config["api_key"],
                                               base_url=model_config["base_url"],
                                               extra_params=model_config["params"],
                                               llm_logs=llm_logs)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "classify":
                validation = validate_workspace_bundle(paths, real_work_dir)
                for warning in validation.get("warnings", []):
                    request.app.state.tasks.append_log(task.id, f"[校验提示] {warning}")
                if not validation.get("ok"):
                    for error in validation.get("errors", []):
                        request.app.state.tasks.append_log(task.id, f"[校验失败] {error}")
                    raise ValueError("\n".join(validation.get("errors", [])) or "classify workspace validation failed")
                t0 = time.time()
                model_cfg_id = payload.get("modelCfgId")
                model_id = resolve_model_id(settings, model_cfg_id)
                result = run_classify(
                    paths,
                    settings,
                    real_work_dir,
                    int(payload.get("maxRounds") or 2),
                    model_cfg_id=model_cfg_id,
                    log_cb=lambda line: request.app.state.tasks.append_log(task.id, line),
                )
                llm_logs.add(scene="材料分类", model=model_id,
                             prompt_summary=f"工作目录: {Path(real_work_dir).name}",
                             response_summary=json.dumps(result, ensure_ascii=False)[:500] if result else "",
                             success=True, elapsed_s=time.time() - t0)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "test-classify-prompt":
                validation = validate_workspace_bundle(paths, real_work_dir)
                for warning in validation.get("warnings", []):
                    request.app.state.tasks.append_log(task.id, f"[校验提示] {warning}")
                if not validation.get("ok"):
                    for error in validation.get("errors", []):
                        request.app.state.tasks.append_log(task.id, f"[校验失败] {error}")
                    raise ValueError("\n".join(validation.get("errors", [])) or "classify prompt validation failed")
                result = run_test_classify(
                    paths,
                    settings,
                    real_work_dir,
                    payload["promptType"],
                    payload["promptContent"],
                    model_cfg_id=payload.get("modelCfgId"),
                    log_cb=lambda line: request.app.state.tasks.append_log(task.id, line),
                )
                request.app.state.tasks.complete(task.id, result)
            elif kind == "factor-json":
                fj_group_size = int(payload.get("groupSize") or 4)
                fj_materials = payload.get("materials") or None
                result = run_factor_json(paths, real_work_dir, group_size=fj_group_size, materials=fj_materials)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "review-rule":
                t0 = time.time()
                validation = validate_workspace_bundle(paths, real_work_dir)
                for warning in validation.get("warnings", []):
                    request.app.state.tasks.append_log(task.id, f"[校验提示] {warning}")
                if not validation.get("ok"):
                    for error in validation.get("errors", []):
                        request.app.state.tasks.append_log(task.id, f"[校验失败] {error}")
                    raise ValueError("\n".join(validation.get("errors", [])) or "review-rule workspace validation failed")
                result = run_review_rule(
                    paths,
                    settings,
                    real_work_dir,
                    bool(payload.get("useLlm")),
                    lambda line: request.app.state.tasks.append_log(task.id, line),
                    api_key=payload.get("apiKey"),
                    base_url=payload.get("baseUrl"),
                    model=payload.get("model"),
                    model_cfg_id=payload.get("modelCfgId"),
                    materials=payload.get("materials") or None,
                    task_store=request.app.state.tasks,
                    task_id=task.id,
                )
                llm_logs.add(scene="审查规则生成", model=payload.get("model") or resolve_model_id(settings, payload.get("modelCfgId")),
                             prompt_summary=f"工作目录: {Path(real_work_dir).name}, useLlm={payload.get('useLlm')}",
                             response_summary=json.dumps(result, ensure_ascii=False)[:500] if result else "",
                             success=True, elapsed_s=time.time() - t0)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "regenerate-keypoint":
                result = {
                    "review_rule": payload.get("targetRule", ""),
                    "review_rule_text": payload.get("ruleDesc", ""),
                    "content": payload.get("ruleDesc", ""),
                    "review_conditions": None,
                    "review_rule_js": "",
                    "passreason": "",
                    "nopassreason": "",
                }
                request.app.state.tasks.complete(task.id, result)
            else:
                request.app.state.tasks.fail(task.id, f"unsupported python task kind: {kind}")
        except TaskCancelledError as exc:
            request.app.state.tasks.append_log(task.id, f"[取消] {exc}")
            request.app.state.tasks.mark_cancelled(task.id, str(exc))
        except Exception as exc:
            request.app.state.tasks.append_log(task.id, f"[error] {exc}")
            request.app.state.tasks.fail(task.id, str(exc))
            scene_map = {"generate": "提示词生成", "classify": "材料分类", "review-rule": "审查规则生成",
                         "verify-extraction": "验证提取", "factor-json": "要素JSON生成"}
            llm_logs.add(scene=scene_map.get(kind, kind), model="unknown",
                         prompt_summary=f"任务失败: {kind}", error=str(exc),
                         success=False, elapsed_s=0)

    threading.Thread(target=worker, daemon=True).start()
    return task.model_dump()


@app.get("/api/task-runs/{task_id}")
async def get_task(task_id: str, request: Request, user: Any = Depends(current_user)):
    task = request.app.state.tasks.get(task_id, user.id)
    if not task:
        fail(404, "task not found")
    return task.model_dump()


@app.post("/api/task-runs/{task_id}/cancel")
async def cancel_task_route(task_id: str, request: Request, user: Any = Depends(current_user)):
    task = request.app.state.tasks.request_cancel(task_id, user.id)
    if not task:
        fail(404, "task not found")
    return task.model_dump()


@app.get("/api/task-runs/{task_id}/logs")
async def get_task_logs(task_id: str, request: Request, user: Any = Depends(current_user)):
    logs = request.app.state.tasks.logs(task_id, user.id)
    if logs is None:
        fail(404, "task not found")
    return {"logs": logs}


@app.get("/api/logs")
async def llm_logs(request: Request, page: int = Query(default=1), pageSize: int = Query(default=20), admin: Any = Depends(current_admin)):
    return request.app.state.llm_logs.list(page=page, page_size=pageSize)


@app.delete("/api/logs")
async def clear_llm_logs(request: Request, admin: Any = Depends(current_admin)):
    request.app.state.llm_logs.clear()
    return {"ok": True}


@app.get("/api/cases")
async def cases(request: Request, user: Any = Depends(current_user)):
    return load_case_library(request.app.state.paths, request.app.state.data)


@app.post("/api/cases/import-json")
async def import_cases_json(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    source = load_json(Path(payload["sourcePath"]), {})
    if isinstance(source, list):
        source = {"version": "1.0", "cases": source}
    if not isinstance(source, dict) or not isinstance(source.get("cases"), list):
        fail(400, "invalid case library json")
    cases_list = source["cases"]
    result = request.app.state.data.import_cases(cases_list, overwrite=bool(payload.get("overwrite")))
    total = request.app.state.data.list_cases()
    return {"imported_count": result["imported"], "imported": result["imported"], "skipped": result["skipped"], "failed": 0, "total_cases": len(total)}


@app.post("/api/cases/import-txt")
async def import_cases_txt(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    file_paths = payload.get("filePaths") or []
    imported = 0
    skipped = 0
    failed = 0
    file_results = []
    for raw_path in file_paths:
        path = Path(raw_path)
        if not path.exists():
            failed += 1
            file_results.append({"file": path.name, "added": 0, "skipped": 0, "error": "file not found"})
            continue
        added = 0
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            text = line.strip()
            if not text:
                continue
            try:
                request.app.state.data.create_case(
                    user_id=admin.id,
                    material_name=path.stem,
                    factor_name=f"Line {index}",
                    extraction_rule=text,
                    metadata={"id": str(uuid4()), "material_name": path.stem, "factor_name": f"Line {index}", "extraction_rule": text}
                )
                added += 1
            except Exception:
                skipped += 1
        imported += added
        file_results.append({"file": path.name, "added": added, "skipped": 0})
    total = request.app.state.data.list_cases()
    return {"imported": imported, "skipped": skipped, "failed": failed, "total_cases": len(total), "file_results": file_results}


@app.post("/api/cases/import-excel")
async def import_cases_excel(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    file_path = payload.get("filePath", "")
    if not file_path or not Path(file_path).exists():
        fail(400, "Excel file not found")
    try:
        parsed = parse_excel_for_cases(file_path)
    except Exception as exc:
        fail(400, f"Excel parse error: {exc}")
    cases_list = parsed["cases"]
    result = request.app.state.data.import_cases(cases_list, overwrite=bool(payload.get("overwrite")))
    total = request.app.state.data.list_cases()
    return {
        "item_name": parsed["item_name"],
        "imported": result["imported"],
        "skipped": result["skipped"],
        "total_cases": len(total),
        "summary": parsed["summary"],
    }


@app.get("/api/cases/lookup")
async def lookup_case(request: Request, user: Any = Depends(current_user),
                      item_name: str = Query(""), material_name: str = Query(""),
                      factor_name: str = Query("")):
    result = request.app.state.data.lookup_case(item_name, material_name, factor_name)
    return {"found": result is not None, "case": result}


@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str, request: Request, admin: Any = Depends(current_admin)):
    if not request.app.state.data.delete_case(case_id):
        fail(404, "case not found")
    return {"ok": True}


@app.get("/api/review-rules")
async def review_rules(request: Request, user: Any = Depends(current_user)):
    return load_review_rule_library_file(request.app.state.paths, request.app.state.data)


@app.put("/api/review-rules")
async def save_review_rules(payload: list[Any], request: Request, admin: Any = Depends(current_admin)):
    save_review_rule_library_file(request.app.state.paths, request.app.state.data, payload)
    return {"success": True}


@app.delete("/api/review-rules")
async def clear_review_rules(request: Request, admin: Any = Depends(current_admin)):
    save_review_rule_library_file(request.app.state.paths, request.app.state.data, [])
    return {"success": True}


@app.post("/api/review-rules/import-excel")
async def import_review_rules_excel(payload: dict[str, Any], request: Request, admin: Any = Depends(current_admin)):
    file_path = payload.get("filePath", "")
    if not file_path or not Path(file_path).exists():
        fail(400, "Excel file not found")
    try:
        parsed = parse_excel_for_review_rules(file_path)
    except Exception as exc:
        fail(400, f"Excel parse error: {exc}")
    result = request.app.state.data.import_review_rules_from_excel(parsed["rules"])
    total = request.app.state.data.list_review_rules()
    total_kps = sum(len(g.get("keypoints", [])) for g in total)
    return {
        "item_name": parsed["item_name"],
        "imported": result["imported"],
        "skipped": result["skipped"],
        "total_rules": total_kps,
        "summary": parsed["summary"],
    }


@app.get("/api/review-rules/lookup")
async def lookup_review_rule(request: Request, user: Any = Depends(current_user),
                              item_name: str = Query(""), materialname: str = Query(""),
                              kpname: str = Query("")):
    result = request.app.state.data.lookup_review_rule(item_name, materialname, kpname)
    return {"found": result is not None, "rule": result}


@app.post("/api/invoke/{command}")
async def invoke(command: str, payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    _ensure_user_dirs(paths, user.id)
    work_dir = payload.get("workDir", "")
    real_work_dir = _resolve_user_work_dir(paths, work_dir, user.id)
    if command == "read_factors":
        return read_factors_script(paths, real_work_dir)
    if command == "get_materials":
        root = Path(real_work_dir)
        return [{"name": entry.name, "path": str(entry), "image_count": sum(1 for child in entry.iterdir() if child.is_file())} for entry in root.iterdir() if entry.is_dir()]
    if command == "read_json_file":
        return json.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    if command == "write_json_file":
        target = Path(payload["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload["content"], encoding="utf-8")
        return None
    if command == "save_prompt_file":
        target = Path(payload["filePath"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload["content"], encoding="utf-8")
        return None
    if command == "get_material_categories":
        return [item["name"] for item in collect_workspace_material_dirs(Path(real_work_dir))]
    if command == "get_pending_files":
        return collect_workspace_sample_files(Path(real_work_dir))
    if command == "write_file":
        target = Path(payload["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload["content"], encoding="utf-8")
        return None
    if command == "read_file":
        return Path(payload["path"]).read_text(encoding="utf-8")
    if command == "read_directory":
        root = Path(payload["path"])
        return [
            {
                "name": entry.name,
                "path": str(entry),
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            }
            for entry in root.iterdir()
        ]
    if command == "search_cases":
        query = str(payload.get("query", "")).lower()
        all_cases = request.app.state.data.list_cases()
        return {
            "cases": [
                item for item in all_cases
                if query in json.dumps(item, ensure_ascii=False).lower()
            ]
        }
    if command == "import_cases":
        source_dir = Path(payload.get("sourceDir", ""))
        if not source_dir.exists() or not source_dir.is_dir():
            fail(400, "sourceDir does not exist")
        imported = 0
        for txt_file in source_dir.glob("*.txt"):
            for index, line in enumerate(txt_file.read_text(encoding="utf-8").splitlines(), start=1):
                text = line.strip()
                if not text:
                    continue
                request.app.state.data.create_case(
                    user_id=request.app.state.auth.get_user_by_username("admin").get("id") or "admin",
                    material_name=txt_file.stem,
                    factor_name=f"Line {index}",
                    extraction_rule=text,
                    metadata={"id": str(uuid4()), "material_name": txt_file.stem, "factor_name": f"Line {index}", "extraction_rule": text}
                )
                imported += 1
        total = request.app.state.data.list_cases()
        return {"imported": imported, "total_cases": len(total)}
    fail(404, f"unsupported command: {command}")


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "backend": "python-fastapi",
        "python": {"available": True, "version": sys.version.split()[0], "installable": True},
        "packages": []
    }


@app.post("/api/health/install-packages")
async def install_packages(payload: dict[str, Any], admin: Any = Depends(current_admin)):
    return {"success": True, "output": "Package installation is delegated to the Python environment.", "requires_restart": False}


@app.post("/api/health/install-python")
async def install_python(admin: Any = Depends(current_admin)):
    return {"success": False, "output": "Automatic Python installation is not supported in this backend.", "requires_restart": False}


paths_for_static = get_paths()
if (paths_for_static.web_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=paths_for_static.web_dist / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    index_file = request.app.state.paths.web_dist / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


@app.get("/{path:path}", response_class=HTMLResponse)
async def fallback(path: str, request: Request):
    if path.startswith("api/"):
        fail(404, "Not Found")
    target = request.app.state.paths.web_dist / path
    if target.exists() and target.is_file():
        media_type, _ = mimetypes.guess_type(str(target))
        return FileResponse(target, media_type=media_type or "application/octet-stream")
    index_file = request.app.state.paths.web_dist / "index.html"
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 3000)))
