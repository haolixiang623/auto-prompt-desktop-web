"""
统一数据存储模块 - 所有用户业务数据统一存储在一个 SQLite 数据库中，
按 user_id 隔离，实现多用户数据独立管理。
"""
import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..models.schemas import UserRole
from .paths import get_paths

ph = PasswordHasher()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str) -> Any:
    if not value:
        return None
    return json.loads(value)


# ---------------------------------------------------------------------------
# 单例模式：全局唯一 DataStore 实例
# ---------------------------------------------------------------------------

_data_store: Optional["DataStore"] = None
_store_lock = threading.Lock()


def get_data_store() -> "DataStore":
    """获取全局 DataStore 单例"""
    global _data_store
    if _data_store is None:
        with _store_lock:
            if _data_store is None:
                paths = get_paths()
                _data_store = DataStore(paths.app_db_path)
    return _data_store


# ---------------------------------------------------------------------------
# DataStore 类
# ---------------------------------------------------------------------------

class DataStore:
    """
    统一数据存储：SQLite 单文件，按 user_id 隔离。
    包含 workspaces、tasks、cases、review_rules 四类业务表。
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_tables()
        self._migrate_legacy()
        self._migrate_v3()

    # ------------------------------------------------------------------
    # 底层连接
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        """获取数据库连接（with 自动 commit/close）"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """初始化所有表结构"""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    root_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    result TEXT DEFAULT NULL,
                    error TEXT DEFAULT NULL,
                    logs TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    material_name TEXT DEFAULT '',
                    factor_name TEXT DEFAULT '',
                    extraction_rule TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS review_rules (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT DEFAULT NULL,
                    review_rule TEXT DEFAULT '',
                    review_rule_text TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    review_conditions TEXT DEFAULT NULL,
                    review_rule_js TEXT DEFAULT '',
                    passreason TEXT DEFAULT '',
                    nopassreason TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS god_prompts (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
            """)
        self._ensure_default_admin()

    def _ensure_default_admin(self) -> None:
        """确保默认管理员账户存在"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()
            if row is not None:
                return
            user_id = secrets.token_hex(16)
            now = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO users (id, name, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, "System Admin", "admin", ph.hash("admin123456"), "admin", 1, now)
            )

    def _migrate_legacy(self) -> None:
        """迁移旧版 JSON 文件数据（幂等）"""
        with self._conn() as conn:
            applied = conn.execute(
                "SELECT version FROM schema_version WHERE version = 2"
            ).fetchone()
            if applied is not None:
                return

        paths = get_paths()

        # 迁移 case_library.json
        case_path = paths.data_dir / "case_library.json"
        if case_path.exists():
            try:
                data = json.loads(case_path.read_text(encoding="utf-8"))
                cases = data.get("cases", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            except Exception:
                cases = []
            self._migrate_cases(cases)

        # 迁移 review_rule_library.json
        rules_path = paths.data_dir / "review_rule_library.json"
        if rules_path.exists():
            try:
                rules = json.loads(rules_path.read_text(encoding="utf-8"))
            except Exception:
                rules = []
            self._migrate_review_rules(rules)

        # 迁移 god_prompts 从 settings.json
        self._migrate_god_prompts(paths.settings_path)

        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (2, datetime.utcnow().isoformat())
            )

    def _migrate_cases(self, cases: List[Dict]) -> None:
        """迁移案例数据（幂等：按 extraction_rule 判断是否重复）"""
        if not cases:
            return
        for case in cases:
            rule = case.get("extraction_rule", "")
            if not rule:
                continue
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT id FROM cases WHERE user_id = 'admin' AND extraction_rule = ?",
                    (rule,)
                ).fetchone()
            if exists:
                continue
            self.create_case(
                user_id="admin",
                material_name=case.get("material_name", ""),
                factor_name=case.get("factor_name", ""),
                extraction_rule=rule,
                metadata=case
            )

    def _migrate_review_rules(self, rules: List[Dict]) -> None:
        """迁移审查规则数据（幂等：按 review_rule_text 判断）"""
        if not rules:
            return
        for rule in rules:
            text = rule.get("review_rule_text", "")
            if not text:
                continue
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT id FROM review_rules WHERE user_id = 'admin' AND review_rule_text = ?",
                    (text,)
                ).fetchone()
            if exists:
                continue
            self.create_review_rule(
                user_id="admin",
                review_rule=rule.get("review_rule", ""),
                review_rule_text=text,
                content=rule.get("content", ""),
                review_conditions=rule.get("review_conditions"),
                review_rule_js=rule.get("review_rule_js", ""),
                passreason=rule.get("passreason", ""),
                nopassreason=rule.get("nopassreason", "")
            )

    def _migrate_god_prompts(self, settings_path: Path) -> None:
        """从 settings.json 迁移 god_prompts 到 god_prompts 表（幂等）"""
        if not settings_path.exists():
            return
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            return
        prompts = data.get("god_prompts", {})
        if not prompts:
            return
        for name, content in prompts.items():
            if not content:
                continue
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT id FROM god_prompts WHERE name = ?", (name,)
                ).fetchone()
            if exists:
                continue
            self.save_god_prompt(name, content)

    def _migrate_v3(self) -> None:
        """v3: 为 cases 和 review_rules 添加层级字段（幂等）"""
        with self._conn() as conn:
            applied = conn.execute(
                "SELECT version FROM schema_version WHERE version = 3"
            ).fetchone()
            if applied is not None:
                return
            # cases: 添加 item_name（事项名称）
            try:
                conn.execute("ALTER TABLE cases ADD COLUMN item_name TEXT DEFAULT ''")
            except Exception:
                pass
            # review_rules: 添加 item_name / materialname / kpname
            for col in ("item_name", "materialname", "kpname"):
                try:
                    conn.execute(f"ALTER TABLE review_rules ADD COLUMN {col} TEXT DEFAULT ''")
                except Exception:
                    pass
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (3, datetime.utcnow().isoformat())
            )

    def _admin_id(self) -> Optional[str]:
        """获取 admin 用户的 id"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()
            return row["id"] if row else None

    # ------------------------------------------------------------------
    # 用户相关（供 AuthStore 代理或直接使用）
    # ------------------------------------------------------------------

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, name, username, role, active, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_users(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, name, username, role, active, created_at FROM users ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def create_user(self, name: str, username: str, password: str, role: str = "user") -> Dict:
        user_id = secrets.token_hex(16)
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (id, name, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, name, username, ph.hash(password), role, 1, now)
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"用户名 '{username}' 已存在")
        return self.get_user_by_id(user_id)

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        row = self.get_user_by_username(username)
        if row is None or not row["active"]:
            return None
        try:
            ph.verify(row["password_hash"], password)
        except VerifyMismatchError:
            return None
        return {k: v for k, v in row.items() if k != "password_hash"}

    def reset_password(self, user_id: str, password: str) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (ph.hash(password), user_id)
            )
            return cursor.rowcount > 0

    def update_user_status(self, user_id: str, active: bool) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE users SET active = ? WHERE id = ?",
                (1 if active else 0, user_id)
            )
            return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """删除用户及其所有关联数据（级联删除）"""
        with self._conn() as conn:
            conn.execute("DELETE FROM cases WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM review_rules WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM workspaces WHERE user_id = ?", (user_id,))
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # 会话管理（内存存储 + 数据库持久化 token）
    # ------------------------------------------------------------------

    def create_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    def save_session(self, token: str, user_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, datetime.utcnow().isoformat())
            )

    def get_session_user_id(self, token: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT user_id FROM sessions WHERE token = ?", (token,)
            ).fetchone()
            return row["user_id"] if row else None

    def delete_session(self, token: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def _add_sessions_table(self) -> None:
        """延迟创建 sessions 表（会话较少时用内存即可，此处用表存储更可靠）"""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

    # ------------------------------------------------------------------
    # Workspaces
    # ------------------------------------------------------------------

    def create_workspace(self, user_id: str, workspace_id: str, name: str, root_path: str, description: str = "") -> Dict:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO workspaces (id, user_id, name, description, root_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (workspace_id, user_id, name, description, root_path, now)
            )
        return {
            "id": workspace_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "root_path": root_path,
            "created_at": now
        }

    def get_workspace(self, user_id: str, workspace_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE id = ? AND user_id = ?",
                (workspace_id, user_id)
            ).fetchone()
            return dict(row) if row else None

    def list_workspaces(self, user_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workspaces WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_workspace(self, user_id: str, workspace_id: str) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM workspaces WHERE id = ? AND user_id = ?",
                (workspace_id, user_id)
            )
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(
        self,
        user_id: str,
        task_id: str,
        kind: str,
        workspace_id: Optional[str] = None
    ) -> Dict:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO tasks
                   (id, user_id, workspace_id, kind, status, progress, logs, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, user_id, workspace_id, kind, "pending", 0, "[]", now, now)
            )
        return self._task_row({
            "id": task_id, "user_id": user_id, "workspace_id": workspace_id,
            "kind": kind, "status": "pending", "progress": 0,
            "result": None, "error": None, "logs": "[]",
            "created_at": now, "updated_at": now
        })

    def get_task(self, user_id: str, task_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            ).fetchone()
            return self._task_row(dict(row)) if row else None

    def list_tasks(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        offset = (page - 1) * page_size
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (user_id, page_size, offset)
            ).fetchall()
            return [self._task_row(dict(r)) for r in rows]

    def update_task_status(
        self,
        user_id: str,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        result: Any = None,
        error: Optional[str] = None,
        append_log: Optional[str] = None
    ) -> bool:
        with self._lock:
            task = self.get_task(user_id, task_id)
            if task is None:
                return False

            updates: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
            if status:
                updates["status"] = status
            if progress is not None:
                updates["progress"] = progress
            if result is not None:
                updates["result"] = _json_dumps(result)
            if error is not None:
                updates["error"] = error
            if append_log is not None:
                logs = _json_loads(task["logs"]) or []
                logs.append(append_log)
                updates["logs"] = _json_dumps(logs)

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [task_id, user_id]
            with self._conn() as conn:
                cursor = conn.execute(
                    f"UPDATE tasks SET {set_clause} WHERE id = ? AND user_id = ?",
                    values
                )
                return cursor.rowcount > 0

    def _task_row(self, row: Dict) -> Dict:
        """将数据库行转换为 Task 对象格式"""
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "workspace_id": row.get("workspace_id"),
            "kind": row["kind"],
            "status": row["status"],
            "progress": row["progress"],
            "result": _json_loads(row["result"]) if row.get("result") else None,
            "error": row.get("error"),
            "logs": _json_loads(row["logs"]) or [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ------------------------------------------------------------------
    # Cases
    # ------------------------------------------------------------------

    def create_case(
        self,
        user_id: str,
        material_name: str = "",
        factor_name: str = "",
        extraction_rule: str = "",
        metadata: Optional[Dict] = None,
        item_name: str = ""
    ) -> Dict:
        case_id = secrets.token_hex(16)
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO cases (id, user_id, material_name, factor_name, extraction_rule, metadata, created_at, item_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (case_id, user_id, material_name, factor_name, extraction_rule,
                 _json_dumps(metadata or {}), now, item_name)
            )
        return {
            "id": case_id,
            "user_id": user_id,
            "item_name": item_name,
            "material_name": material_name,
            "factor_name": factor_name,
            "extraction_rule": extraction_rule,
            "metadata": metadata or {},
            "created_at": now,
        }

    def list_cases(self) -> List[Dict]:
        """所有用户的案例（全员可见）"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cases ORDER BY created_at DESC"
            ).fetchall()
            results = []
            for r in rows:
                row = dict(r)
                row["metadata"] = _json_loads(row.get("metadata")) or {}
                results.append(row)
            return results

    def lookup_case(self, item_name: str, material_name: str, factor_name: str) -> Optional[Dict]:
        """按 (item_name, material_name, factor_name) 精确查找案例"""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT * FROM cases
                   WHERE item_name = ? AND material_name = ? AND factor_name = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (item_name, material_name, factor_name)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["metadata"] = _json_loads(result.get("metadata")) or {}
            return result

    def delete_case(self, case_id: str) -> bool:
        """删除案例（仅 admin 可操作）"""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            return cursor.rowcount > 0

    def import_cases(
        self,
        cases: List[Dict],
        overwrite: bool = False
    ) -> Dict[str, int]:
        """批量导入案例（写入 admin 名下；全员可读）"""
        admin_id = self._admin_id() or "admin"
        imported = 0
        skipped = 0
        for case in cases:
            rule = case.get("extraction_rule", "")
            if not rule:
                skipped += 1
                continue
            with self._conn() as conn:
                exists = conn.execute(
                    "SELECT id FROM cases WHERE extraction_rule = ?",
                    (rule,)
                ).fetchone()
            if exists and not overwrite:
                skipped += 1
                continue
            self.create_case(
                user_id=admin_id,
                material_name=case.get("material_name", ""),
                factor_name=case.get("factor_name", ""),
                extraction_rule=rule,
                metadata=case,
                item_name=case.get("item_name", "")
            )
            imported += 1
        return {"imported": imported, "skipped": skipped, "total": len(cases)}

    # ------------------------------------------------------------------
    # Review Rules
    # ------------------------------------------------------------------

    def create_review_rule(
        self,
        user_id: str,
        review_rule: str = "",
        review_rule_text: str = "",
        content: str = "",
        review_conditions: Optional[Any] = None,
        review_rule_js: str = "",
        passreason: str = "",
        nopassreason: str = "",
        workspace_id: Optional[str] = None,
        item_name: str = "",
        materialname: str = "",
        kpname: str = ""
    ) -> Dict:
        rule_id = secrets.token_hex(16)
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO review_rules
                   (id, user_id, workspace_id, review_rule, review_rule_text, content,
                    review_conditions, review_rule_js, passreason, nopassreason, created_at,
                    item_name, materialname, kpname)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rule_id, user_id, workspace_id, review_rule, review_rule_text, content,
                 _json_dumps(review_conditions) if review_conditions is not None else None,
                 review_rule_js, passreason, nopassreason, now,
                 item_name, materialname, kpname)
            )
        return {
            "id": rule_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "item_name": item_name,
            "materialname": materialname,
            "kpname": kpname,
            "review_rule": review_rule,
            "review_rule_text": review_rule_text,
            "content": content,
            "review_conditions": review_conditions,
            "review_rule_js": review_rule_js,
            "passreason": passreason,
            "nopassreason": nopassreason,
            "created_at": now,
        }

    def lookup_review_rule(self, item_name: str, materialname: str, kpname: str) -> Optional[Dict]:
        """按 (item_name, materialname, kpname) 精确查找审查规则"""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT * FROM review_rules
                   WHERE item_name = ? AND materialname = ? AND kpname = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (item_name, materialname, kpname)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["review_conditions"] = _json_loads(result["review_conditions"]) if result.get("review_conditions") else None
            return result

    def import_review_rules_from_excel(self, rules: List[Dict]) -> Dict[str, int]:
        """从 Excel 解析结果批量导入审查规则（追加模式，按 item_name+materialname+kpname 去重）"""
        admin_id = self._admin_id() or "admin"
        imported = 0
        skipped = 0
        for group in rules:
            item_name = group.get("item_name", "")
            materialname = group.get("materialname", "")
            for kp in group.get("keypoints", []):
                kpname = kp.get("kpname", "")
                if not kpname:
                    skipped += 1
                    continue
                existing = self.lookup_review_rule(item_name, materialname, kpname)
                if existing:
                    skipped += 1
                    continue
                self.create_review_rule(
                    user_id=admin_id,
                    review_rule=kp.get("review_rule", ""),
                    review_rule_text=kp.get("review_rule_text", ""),
                    content=kp.get("content", ""),
                    review_conditions=kp.get("review_conditions"),
                    review_rule_js=kp.get("review_rule_js", ""),
                    passreason=kp.get("passreason", ""),
                    nopassreason=kp.get("nopassreason", ""),
                    item_name=item_name,
                    materialname=materialname,
                    kpname=kpname,
                )
                imported += 1
        return {"imported": imported, "skipped": skipped}

    def list_review_rules(self) -> List[Dict]:
        """所有审查规则，按 item_name → materialname 分组返回层级结构"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM review_rules ORDER BY created_at"
            ).fetchall()
        # 按 (item_name, materialname) 分组重建层级
        from collections import OrderedDict
        groups: OrderedDict = OrderedDict()
        for r in rows:
            row = dict(r)
            row["review_conditions"] = _json_loads(row["review_conditions"]) if row.get("review_conditions") else None
            item = row.get("item_name") or ""
            mat = row.get("materialname") or ""
            key = (item, mat)
            if key not in groups:
                groups[key] = {"item_name": item, "materialname": mat, "keypoints": []}
            kp = {k: v for k, v in row.items() if k not in ("user_id", "workspace_id", "item_name", "materialname")}
            groups[key]["keypoints"].append(kp)
        return list(groups.values())

    def save_review_rules(self, rules: List[Dict]) -> bool:
        """全量替换审查规则（写入 admin 名下；全员可读）
        接受层级格式: [{ item_name, materialname, keypoints: [{...}] }]
        也兼容扁平格式: [{ review_rule, review_rule_text, ... }]
        """
        admin_id = self._admin_id() or "admin"
        with self._conn() as conn:
            conn.execute("DELETE FROM review_rules")
        for rule in rules:
            keypoints = rule.get("keypoints")
            if isinstance(keypoints, list):
                # 层级格式：每个 keypoint 单独存一行
                item_name = rule.get("item_name", "")
                materialname = rule.get("materialname", "")
                for kp in keypoints:
                    self.create_review_rule(
                        user_id=admin_id,
                        review_rule=kp.get("review_rule", ""),
                        review_rule_text=kp.get("review_rule_text", ""),
                        content=kp.get("content", ""),
                        review_conditions=kp.get("review_conditions"),
                        review_rule_js=kp.get("review_rule_js", ""),
                        passreason=kp.get("passreason", ""),
                        nopassreason=kp.get("nopassreason", ""),
                        workspace_id=rule.get("workspace_id"),
                        item_name=item_name,
                        materialname=materialname,
                        kpname=kp.get("kpname", "")
                    )
            else:
                # 扁平格式（旧数据兼容）
                self.create_review_rule(
                    user_id=admin_id,
                    review_rule=rule.get("review_rule", ""),
                    review_rule_text=rule.get("review_rule_text", ""),
                    content=rule.get("content", ""),
                    review_conditions=rule.get("review_conditions"),
                    review_rule_js=rule.get("review_rule_js", ""),
                    passreason=rule.get("passreason", ""),
                    nopassreason=rule.get("nopassreason", ""),
                    workspace_id=rule.get("workspace_id"),
                    item_name=rule.get("item_name", ""),
                    materialname=rule.get("materialname", ""),
                    kpname=rule.get("kpname", "")
                )
        return True

    def clear_review_rules(self) -> bool:
        """清空所有审查规则（仅 admin 可操作）"""
        with self._conn() as conn:
            conn.execute("DELETE FROM review_rules")
        return True

    # ------------------------------------------------------------------
    # God Prompts（全员可读，admin 可写）
    # ------------------------------------------------------------------

    def list_god_prompts(self) -> List[Dict]:
        """列出所有 god prompts（全员可见）"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM god_prompts ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    def save_god_prompt(self, name: str, content: str) -> Dict:
        """创建或更新一条 god prompt（upsert）"""
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM god_prompts WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE god_prompts SET content = ?, updated_at = ? WHERE name = ?",
                    (content, now, name)
                )
                row = conn.execute(
                    "SELECT * FROM god_prompts WHERE name = ?", (name,)
                ).fetchone()
                return dict(row)
            else:
                gp_id = secrets.token_hex(8)
                conn.execute(
                    "INSERT INTO god_prompts (id, name, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (gp_id, name, content, now, now)
                )
                row = conn.execute(
                    "SELECT * FROM god_prompts WHERE name = ?", (name,)
                ).fetchone()
                return dict(row)

    def delete_god_prompt(self, name: str) -> bool:
        """删除一条 god prompt（仅 admin 可操作）"""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM god_prompts WHERE name = ?", (name,))
            return cursor.rowcount > 0
