# 任务管理模块 - 对应 Rust tasks.rs
# 持久化：所有操作通过 DataStore (SQLite) 完成
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.data import DataStore

from ..models.schemas import Task, TaskKind, TaskRecord, TaskStatus


class TaskStore:
    """任务存储管理 - SQLite 持久化，按 user_id 隔离"""

    def __init__(self, task_root: Path, data_store: Optional["DataStore"] = None):
        self.task_root = Path(task_root)
        self.task_root.mkdir(parents=True, exist_ok=True)
        self._data_store = data_store
        self._records: Dict[str, TaskRecord] = {}
        self._lock = threading.RLock()

    def set_data_store(self, data_store: "DataStore") -> None:
        """延迟注入 DataStore（在 lifespan 中由 main.py 传入）"""
        self._data_store = data_store

    def _persist_to_json(self, record: TaskRecord) -> None:
        """同时写一份 JSON 文件备份（文件系统不变）"""
        task_path = self.task_root / record.task.owner_user_id / f"{record.task.id}.json"
        task_path.parent.mkdir(parents=True, exist_ok=True)
        with open(task_path, "w", encoding="utf-8") as f:
            data = {
                "task": {
                    "id": record.task.id,
                    "kind": record.task.kind.value,
                    "status": record.task.status.value,
                    "progress": record.task.progress,
                    "owner_user_id": record.task.owner_user_id,
                    "workspace_id": record.task.workspace_id,
                    "created_at": record.task.created_at.isoformat(),
                    "updated_at": record.task.updated_at.isoformat(),
                    "result": record.task.result,
                    "error": record.task.error
                },
                "logs": record.logs
            }
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create(self, kind: TaskKind, owner_user_id: str, data_store: Optional["DataStore"] = None) -> Task:
        """创建新任务"""
        now = datetime.utcnow()
        task = Task(
            kind=kind,
            owner_user_id=owner_user_id,
            workspace_id=None,
            created_at=now,
            updated_at=now
        )
        record = TaskRecord(task=task, logs=[])

        with self._lock:
            self._records[task.id] = record
            self._persist_to_json(record)

        if data_store is not None:
            self._data_store = data_store
        if self._data_store is not None:
            try:
                self._data_store.create_task(owner_user_id, task.id, kind.value, workspace_id=None)
            except Exception:
                pass

        return task

    def get(self, task_id: str, owner_user_id: str) -> Optional[Task]:
        """获取任务（需要验证所有者）"""
        with self._lock:
            record = self._records.get(task_id)
            if record and record.task.owner_user_id == owner_user_id:
                return record.task
            return None

    def logs(self, task_id: str, owner_user_id: str) -> Optional[List[str]]:
        """获取任务日志"""
        with self._lock:
            record = self._records.get(task_id)
            if record and record.task.owner_user_id == owner_user_id:
                return record.logs.copy()
            return None

    def _update_task(self, task_id: str, **kwargs) -> bool:
        """更新任务字段"""
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return False

            task_data = record.task.model_dump()
            task_data.update(kwargs)
            task_data["updated_at"] = datetime.utcnow()

            record.task = Task(**task_data)
            self._persist_to_json(record)

            if self._data_store is not None:
                self._data_store.update_task_status(
                    user_id=record.task.owner_user_id,
                    task_id=task_id,
                    status=kwargs.get("status", record.task.status.value),
                    progress=kwargs.get("progress"),
                    result=kwargs.get("result"),
                    error=kwargs.get("error")
                )
            return True

    def mark_running(self, task_id: str, progress: Optional[int] = None) -> bool:
        """标记任务为运行中"""
        return self._update_task(task_id, status=TaskStatus.RUNNING, progress=progress)

    def set_progress(self, task_id: str, progress: int) -> bool:
        """设置任务进度"""
        return self._update_task(task_id, progress=progress)

    def append_log(self, task_id: str, line: str) -> bool:
        """追加任务日志"""
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return False

            record.logs.append(line)
            record.task.updated_at = datetime.utcnow()
            self._persist_to_json(record)

            if self._data_store is not None:
                self._data_store.update_task_status(
                    user_id=record.task.owner_user_id,
                    task_id=task_id,
                    status=record.task.status.value,
                    append_log=line
                )
            return True

    def complete(self, task_id: str, result: dict) -> bool:
        """标记任务完成"""
        return self._update_task(
            task_id,
            status=TaskStatus.SUCCEEDED,
            progress=100,
            result=result,
            error=None
        )

    def fail(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        return self._update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=error
        )

    def list_by_user(self, owner_user_id: str, page: int = 1, page_size: int = 20) -> List[Task]:
        """列出用户的任务"""
        with self._lock:
            tasks = [
                r.task for r in self._records.values()
                if r.task.owner_user_id == owner_user_id
            ]
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            start = (page - 1) * page_size
            end = start + page_size
            return tasks[start:end]
