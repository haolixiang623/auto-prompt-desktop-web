from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
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


DEFAULT_MODELS = [
    {"id": "1", "name": "Qwen VL Max", "model_id": "qwen-vl-max", "type": "vl", "params": []},
    {"id": "2", "name": "Qwen VL Plus", "model_id": "qwen-vl-plus", "type": "vl", "params": []},
    {"id": "3", "name": "Qwen2.5 VL 72B", "model_id": "qwen2.5-vl-72b-instruct", "type": "vl", "params": []},
    {"id": "4", "name": "Qwen Plus (Text)", "model_id": "qwen-plus", "type": "text", "params": []},
    {"id": "5", "name": "Qwen Max (Text)", "model_id": "qwen-max", "type": "text", "params": []},
]


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
        self._sessions: dict[str, str] = {}
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)"
            )
            conn.commit()
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

    def create_session(self, user: Any) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user.id
        return token

    def get_user_from_token(self, token: str) -> Any:
        user_id = self._sessions.get(token)
        if not user_id:
            return None
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT id, name, username, role, active, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_user(row) if row else None

    def delete_session(self, token: str) -> None:
        self._sessions.pop(token, None)

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
            return cursor.rowcount > 0

    def update_user_status(self, user_id: str, active: bool) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
            conn.commit()
            return cursor.rowcount > 0


class TaskStore:
    def __init__(self, task_root: Path):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._logs: dict[str, list[str]] = {}

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
        self._tasks[task_id] = task
        self._logs[task_id] = []
        return task

    def get(self, task_id: str, owner_user_id: str):
        task = self._tasks.get(task_id)
        return task if task and task.owner_user_id == owner_user_id else None

    def logs(self, task_id: str, owner_user_id: str):
        task = self.get(task_id, owner_user_id)
        return list(self._logs.get(task_id, [])) if task else None

    def mark_running(self, task_id: str, progress: int = 0):
        task = self._tasks.get(task_id)
        if task:
            task.status = "running"
            task.progress = progress

    def append_log(self, task_id: str, line: str):
        if task_id in self._logs:
            self._logs[task_id].append(line)

    def complete(self, task_id: str, result: Any):
        task = self._tasks.get(task_id)
        if task:
            task.status = "succeeded"
            task.progress = 100
            task.result = result
            task.error = None

    def fail(self, task_id: str, error: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = "failed"
            task.error = error


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
        "llm_timeout",
    )

    def __init__(self, local_path: Path, project_path: Path) -> None:
        self.local_path = local_path
        self.project_path = project_path

    def load_front(self) -> dict[str, Any]:
        project = load_json(self.project_path, {})
        local = load_json(self.local_path, {})
        settings = {
            "api_key": local["api_key"] if "api_key" in local else os.environ.get("DASHSCOPE_API_KEY", ""),
            "api_key_configured": False,
            "default_model_id": local.get("default_model_id", project.get("default_model_id", "1")),
            "model_name": local.get("model_name", project.get("model_name", "qwen-vl-max")),
            "models": local.get("models", project.get("models", DEFAULT_MODELS)),
            "god_prompt": local.get("god_prompt", project.get("god_prompt", PromptBundle.classify)),
            "extract_god_prompt": local.get("extract_god_prompt", project.get("extract_god_prompt", PromptBundle.extract)),
            "llm_timeout": local.get("llm_timeout", project.get("llm_timeout", 120)),
        }
        settings["api_key_configured"] = bool(settings["api_key"])
        selected = next((m for m in settings["models"] if m.get("id") == settings["default_model_id"]), None)
        if selected:
            settings["model_name"] = selected.get("model_id", settings["model_name"])
        return settings

    def save_front(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_front()
        current.update({k: v for k, v in payload.items() if k in self.FRONT_FIELDS})
        current["api_key_configured"] = bool(current["api_key"])
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


def resolve_model_id(settings: dict[str, Any], model_cfg_id: Optional[str]) -> str:
    """Resolve a modelCfgId (string id from frontend) to the actual model_id string."""
    if model_cfg_id:
        for m in settings.get("models", []):
            if m.get("id") == model_cfg_id:
                return m.get("model_id", settings["model_name"])
    return settings["model_name"]


def base64_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run_verify_extraction(material_dir: Path, prompt_text: str, model_id: str, api_key: str,
                          llm_logs: Optional[LlmLogStore] = None) -> dict[str, Any]:
    """Call Qwen VL to extract data from the first image using the given prompt."""
    image_path = find_media_file(material_dir)
    if image_path is None:
        return {"success": False, "error": "no image found in material directory"}

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
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


def run_generate_prompt(paths: Any, settings: dict[str, Any], work_dir: str, material_name: Optional[str]) -> dict[str, Any]:
    material_dir = Path(work_dir) / material_name if material_name else Path(work_dir)
    user_id = _resolve_user_id_from_work_dir(paths, work_dir)
    script = paths.skills_dir / "doc-extract-prompt-gen" / "generate_prompt.py"
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": settings["api_key"],
        "OPENAI_API_KEY": settings["api_key"],
        "OPENAI_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "MODEL_NAME": settings["model_name"],
        "LLM_TIMEOUT": str(settings.get("llm_timeout", 120)),
        "EXTRACT_GOD_PROMPT": settings["extract_god_prompt"],
        "AUTO_PROMPT_SKILLS_DIR": str(paths.skills_dir),
    }
    args = [sys.executable, str(script), str(material_dir)]
    if material_name:
        args.append(material_name)
    output = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="ignore", env=env)
    if output.returncode != 0:
        raise ValueError(output.stderr.strip() or output.stdout.strip() or "generate prompt failed")
    # 读取生成的提示词内容
    raw_output = material_dir / f"{material_dir.name}--要素提取完整提示词.txt"
    prompt_template = ""
    if raw_output.exists():
        prompt_template = raw_output.read_text(encoding="utf-8")
    if not prompt_template.strip():
        raise ValueError(f"generated prompt is empty: {raw_output}")
    # 保存到用户隔离输出目录
    prompts_dir = paths.user_output_root / user_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\u4e00-\u9fff-]", "_", material_dir.name)
    output_file = prompts_dir / f"{safe_name}--要素提取完整提示词.txt"
    output_file.write_text(prompt_template, encoding="utf-8")
    return {
        "output_file": str(output_file),
        "factors_count": len(read_factors_script(paths, str(material_dir))),
        "images_count": sum(1 for entry in material_dir.iterdir() if entry.is_file() and entry.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".pdf"}),
        "prompt_template": prompt_template,
    }


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


def run_classify(paths: Any, settings: dict[str, Any], work_dir: str, max_rounds: int, log_cb: Optional[Any] = None) -> dict[str, Any]:
    script = paths.skills_dir / "material-classifier" / "classify_materials.py"
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": settings["api_key"],
        "CLASSIFY_MODEL_NAME": settings["model_name"],
        "CLASSIFY_GOD_PROMPT": settings["god_prompt"],
    }
    run_lines([sys.executable, str(script), work_dir, str(max_rounds)], env, work_dir, log_cb)
    report_path = Path(work_dir) / "classification_report.json"
    return load_json(report_path, {})


def run_test_classify(paths: Any, settings: dict[str, Any], work_dir: str, prompt_type: str, prompt_content: str, log_cb: Optional[Any] = None) -> dict[str, Any]:
    script = paths.skills_dir / "material-classifier" / "classify_materials.py"
    prompt_path = Path(work_dir) / f".test_prompt_{prompt_type}.txt"
    prompt_path.write_text(prompt_content, encoding="utf-8")
    env = {
        **os.environ,
        "DASHSCOPE_API_KEY": settings["api_key"],
        "CLASSIFY_MODEL_NAME": settings["model_name"],
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
    materials: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    script = paths.skills_dir / "review-rule-generator" / "generate_review_rule.py"
    cmd = [sys.executable, str(script), work_dir]
    if use_llm:
        resolved_api_key = api_key if api_key is not None else settings["api_key"]
        resolved_base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        resolved_model = model or settings["model_name"]
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
    lines = run_lines(cmd, os.environ.copy(), None, log_cb)
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
    return {"token": request.app.state.auth.create_session(user), "user": user_to_json(user)}


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


@app.get("/api/workspaces/materials")
async def workspace_materials(workDir: str = Query(...), request: Request = None, user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, workDir, user.id)
    root = Path(real_dir)
    result = []
    for entry in root.iterdir():
        if entry.is_dir():
            count = sum(1 for child in entry.iterdir() if child.is_file() and child.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".pdf"})
            if count:
                result.append({"name": entry.name, "path": str(entry), "image_count": count})
    return {"data": sorted(result, key=lambda item: item["name"])}


@app.get("/api/workspaces/factors")
async def workspace_factors(request: Request, workDir: str = Query(...), user: Any = Depends(current_user)):
    paths = request.app.state.paths
    real_dir = _resolve_user_work_dir(paths, workDir, user.id)
    return {"data": read_factors_script(paths, real_dir)}


@app.get("/api/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, request: Request, user: Any = Depends(current_user)):
    return workspace_to_json(request.app.state.workspaces.get_workspace(user.id, workspace_id))


@app.post("/api/generate/prompt")
async def generate_prompt(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    settings = request.app.state.ui_settings.load_front()
    paths = request.app.state.paths
    _ensure_user_dirs(paths, user.id)
    real_work_dir = _resolve_user_work_dir(paths, payload["workDir"], user.id)
    llm_logs = request.app.state.llm_logs
    start = time.time()
    try:
        data = run_generate_prompt(paths, settings, real_work_dir, payload.get("materialName"))
        llm_logs.add(scene="提示词生成", model=settings["model_name"],
                     prompt_summary=f"材料: {payload.get('materialName', '全部')}", 
                     response_summary=data.get("prompt_template", "")[:500],
                     success=True, elapsed_s=time.time() - start)
    except ValueError as exc:
        llm_logs.add(scene="提示词生成", model=settings["model_name"],
                     prompt_summary=f"材料: {payload.get('materialName', '全部')}",
                     error=str(exc), success=False, elapsed_s=time.time() - start)
        fail(400, str(exc))
    return {"data": data}


@app.post("/api/generate/verify")
async def generate_verify(payload: dict[str, Any], request: Request, user: Any = Depends(current_user)):
    settings = request.app.state.ui_settings.load_front()
    paths = request.app.state.paths
    # materialDir 可能是前端传回的后端返回的路径（已包含 workspaces/{user_id}/...）
    # 或者是用户编辑后的路径；直接使用（不做二次映射避免路径错误）
    material_dir = Path(payload["materialDir"])
    prompt_text = payload.get("promptText", "")
    model_cfg_id = payload.get("modelCfgId")
    model_id = resolve_model_id(settings, model_cfg_id)
    result = run_verify_extraction(material_dir, prompt_text, model_id, settings["api_key"],
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
    return FileResponse(target, media_type=media_type or "application/octet-stream", filename=target.name)


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
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
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
                t0 = time.time()
                result = run_generate_prompt(paths, settings, real_work_dir, payload.get("materialName"))
                llm_logs.add(scene="提示词生成", model=settings["model_name"],
                             prompt_summary=f"材料: {payload.get('materialName', '全部')}",
                             response_summary=result.get("prompt_template", "")[:500],
                             success=True, elapsed_s=time.time() - t0)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "verify-extraction":
                material_dir = Path(payload["materialDir"])
                prompt_text = payload.get("promptText", "")
                model_cfg_id = payload.get("modelCfgId")
                model_id = resolve_model_id(settings, model_cfg_id)
                result = run_verify_extraction(material_dir, prompt_text, model_id, settings["api_key"],
                                               llm_logs=llm_logs)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "classify":
                t0 = time.time()
                result = run_classify(paths, settings, real_work_dir, int(payload.get("maxRounds") or 2), lambda line: request.app.state.tasks.append_log(task.id, line))
                llm_logs.add(scene="材料分类", model=settings["model_name"],
                             prompt_summary=f"工作目录: {Path(real_work_dir).name}",
                             response_summary=json.dumps(result, ensure_ascii=False)[:500] if result else "",
                             success=True, elapsed_s=time.time() - t0)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "test-classify-prompt":
                result = run_test_classify(paths, settings, real_work_dir, payload["promptType"], payload["promptContent"], lambda line: request.app.state.tasks.append_log(task.id, line))
                request.app.state.tasks.complete(task.id, result)
            elif kind == "factor-json":
                fj_group_size = int(payload.get("groupSize") or 4)
                fj_materials = payload.get("materials") or None
                result = run_factor_json(paths, real_work_dir, group_size=fj_group_size, materials=fj_materials)
                request.app.state.tasks.complete(task.id, result)
            elif kind == "review-rule":
                t0 = time.time()
                result = run_review_rule(
                    paths,
                    settings,
                    real_work_dir,
                    bool(payload.get("useLlm")),
                    lambda line: request.app.state.tasks.append_log(task.id, line),
                    api_key=payload.get("apiKey"),
                    base_url=payload.get("baseUrl"),
                    model=payload.get("model"),
                    materials=payload.get("materials") or None,
                )
                llm_logs.add(scene="审查规则生成", model=payload.get("model") or settings["model_name"],
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
        names = []
        for item in read_factors_script(paths, real_work_dir):
            if item.get("material"):
                names.append(item["material"])
        return sorted(list(dict.fromkeys(names)))
    if command == "get_pending_files":
        root = Path(real_work_dir)
        for name in ("待分类材料", "待分类"):
            if (root / name).exists():
                root = root / name
                break
        return [{"name": entry.name, "path": str(entry), "size": entry.stat().st_size} for entry in root.iterdir() if entry.is_file()]
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
