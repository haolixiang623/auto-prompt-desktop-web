# 工作空间服务 - 对应 Rust workspace.rs
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel

from ..core.paths import get_paths


class WorkspaceFile(BaseModel):
    """工作空间文件"""
    relative_path: str
    size: int
    is_dir: bool


class WorkspaceSummary(BaseModel):
    """工作空间摘要"""
    id: str
    name: str
    root_path: str
    created_at: datetime
    files: List[WorkspaceFile]


class UploadedBlob(BaseModel):
    """上传的文件块"""
    original_name: str
    relative_path: str
    content: bytes


class WorkspaceService:
    """工作空间服务"""
    
    def __init__(self):
        self.paths = get_paths()
    
    def _user_workspace_root(self, user_id: str) -> Path:
        """获取用户工作空间根目录"""
        return self.paths.workspace_root / user_id
    
    def _user_upload_root(self, user_id: str) -> Path:
        """获取用户上传根目录"""
        return self.paths.upload_root / user_id
    
    def create_workspace(
        self,
        user_id: str,
        name: Optional[str] = None,
        uploads: List[UploadedBlob] = None
    ) -> WorkspaceSummary:
        """创建工作空间"""
        uploads = uploads or []
        workspace_id = str(uuid4())
        root = self._user_workspace_root(user_id) / workspace_id
        root.mkdir(parents=True, exist_ok=True)
        
        # 查找共享前缀
        shared_prefix = self._shared_workspace_prefix(uploads)
        
        # 保存上传的文件
        for upload in uploads:
            relative_source = self._strip_workspace_prefix(upload.relative_path, shared_prefix)
            relative_path = self._sanitize_relative_path(relative_source)
            target_path = root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_path, "wb") as f:
                f.write(upload.content)
        
        # 返回工作空间摘要
        summary = self.get_workspace(user_id, workspace_id)
        if name:
            summary.name = name
        else:
            summary.name = f"workspace-{workspace_id}"
        
        return summary
    
    def save_temp_uploads(self, user_id: str, uploads: List[UploadedBlob]) -> List[str]:
        """保存临时上传文件"""
        upload_root = self._user_upload_root(user_id) / str(uuid4())
        upload_root.mkdir(parents=True, exist_ok=True)
        
        stored_paths = []
        for upload in uploads:
            relative_path = self._sanitize_relative_path(upload.relative_path)
            file_path = upload_root / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(upload.content)
            
            stored_paths.append(str(file_path))
        
        return stored_paths
    
    def get_workspace(self, user_id: str, workspace_id: str) -> WorkspaceSummary:
        """获取工作空间信息"""
        root = self._user_workspace_root(user_id) / workspace_id
        if not root.exists():
            raise ValueError("工作空间不存在")
        
        stat = root.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        
        return WorkspaceSummary(
            id=workspace_id,
            name=f"workspace-{workspace_id}",
            root_path=str(root),
            created_at=created_at,
            files=self._scan_files(root)
        )
    
    def _scan_files(self, root: Path) -> List[WorkspaceFile]:
        """扫描目录文件"""
        files = []
        self._scan_dir(root, root, files)
        files.sort(key=lambda f: f.relative_path)
        return files
    
    def _scan_dir(self, root: Path, current: Path, files: List[WorkspaceFile]) -> None:
        """递归扫描目录"""
        if not current.exists():
            return
        
        for entry in os.scandir(current):
            relative_path = str(Path(entry.path).relative_to(root)).replace("\\", "/")
            stat = entry.stat()
            
            files.append(WorkspaceFile(
                relative_path=relative_path,
                size=stat.st_size,
                is_dir=entry.is_dir()
            ))
            
            if entry.is_dir():
                self._scan_dir(root, Path(entry.path), files)
    
    def _sanitize_relative_path(self, relative_path: str) -> str:
        """清理相对路径"""
        path = Path(relative_path.replace("\\", "/"))
        
        if path.is_absolute():
            raise ValueError("上传路径不能是绝对路径")
        
        # 检查是否包含 ..
        for part in path.parts:
            if part == "..":
                raise ValueError("上传路径不能包含 ..")
        
        return str(path)
    
    def _shared_workspace_prefix(self, uploads: List[UploadedBlob]) -> Optional[str]:
        """查找共享的工作空间前缀"""
        if not uploads:
            return None
        
        prefix = None
        
        for upload in uploads:
            normalized = upload.relative_path.replace("\\", "/")
            parts = [p for p in normalized.split("/") if p]
            
            if len(parts) < 2:
                return None
            
            first = parts[0]
            
            if prefix is None:
                prefix = first
            elif prefix != first:
                return None
        
        return prefix
    
    def _strip_workspace_prefix(self, relative_path: str, prefix: Optional[str]) -> str:
        """去除工作空间前缀"""
        if prefix is None:
            return relative_path
        
        prefix_with_slash = f"{prefix}/"
        if relative_path.startswith(prefix_with_slash):
            return relative_path[len(prefix_with_slash):]
        
        if relative_path == prefix:
            return relative_path
        
        return relative_path
