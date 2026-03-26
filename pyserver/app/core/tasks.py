# 任务管理模块 - 对应 Rust tasks.rs
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.schemas import Task, TaskKind, TaskRecord, TaskStatus


class TaskStore:
    """任务存储管理 - 支持内存缓存和文件持久化"""
    
    def __init__(self, task_root: Path):
        self.task_root = Path(task_root)
        self.task_root.mkdir(parents=True, exist_ok=True)
        
        # 内存存储 + 锁
        self._records: Dict[str, TaskRecord] = {}
        self._lock = threading.RLock()
        
        # 从磁盘恢复任务
        self._restore_records()
    
    def _restore_records(self) -> None:
        """从磁盘恢复任务记录"""
        if not self.task_root.exists():
            return
        
        for user_dir in self.task_root.iterdir():
            if not user_dir.is_dir():
                continue
            
            for task_file in user_dir.glob("*.json"):
                try:
                    with open(task_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        record = TaskRecord(**data)
                        self._records[record.task.id] = record
                except Exception as e:
                    print(f"Failed to restore task from {task_file}: {e}")
    
    def _task_path(self, task: Task) -> Path:
        """获取任务文件路径"""
        return self.task_root / task.owner_user_id / f"{task.id}.json"
    
    def _persist(self, record: TaskRecord) -> None:
        """持久化任务记录到磁盘"""
        task_path = self._task_path(record.task)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(task_path, "w", encoding="utf-8") as f:
            # 转换为可序列化的字典
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
    
    def create(self, kind: TaskKind, owner_user_id: str, workspace_id: Optional[str] = None) -> Task:
        """创建新任务"""
        now = datetime.utcnow()
        task = Task(
            kind=kind,
            owner_user_id=owner_user_id,
            workspace_id=workspace_id,
            created_at=now,
            updated_at=now
        )
        
        record = TaskRecord(task=task, logs=[])
        
        with self._lock:
            self._records[task.id] = record
            self._persist(record)
        
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
            
            # 更新字段
            task_data = record.task.model_dump()
            task_data.update(kwargs)
            task_data["updated_at"] = datetime.utcnow()
            
            # 重新创建Task对象
            record.task = Task(**task_data)
            
            # 持久化
            self._persist(record)
            return True
    
    def mark_running(self, task_id: str, progress: Optional[int] = None) -> bool:
        """标记任务为运行中"""
        return self._update_task(
            task_id, 
            status=TaskStatus.RUNNING,
            progress=progress
        )
    
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
            self._persist(record)
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
            # 按时间倒序排序
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            return tasks[start:end]
