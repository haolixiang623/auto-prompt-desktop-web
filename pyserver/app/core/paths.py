# 路径管理模块 - 对应 Rust paths.rs
import os
from pathlib import Path
from typing import Optional


class AppPaths:
    """应用程序路径管理"""
    
    def __init__(self):
        # 基础目录
        self.repo_root = Path(os.environ.get("AUTO_PROMPT_REPO_ROOT", "/app"))
        self.skills_dir = Path(os.environ.get("AUTO_PROMPT_SKILLS_DIR", self.repo_root / "skills"))
        self.data_dir = Path(os.environ.get("AUTO_PROMPT_DATA_DIR", "/data"))
        
        # 派生路径
        self.workspace_root = self.data_dir / "workspaces"
        self.upload_root = self.data_dir / "uploads"
        self.task_root = self.data_dir / "tasks"
        self.auth_db_path = self.data_dir / "auth.db"
        self.settings_path = self.data_dir / "settings.json"
        
        # 前端资源路径
        self.web_dist = Path(os.environ.get("AUTO_PROMPT_WEB_DIST", self.repo_root / "dist"))
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for path in [self.data_dir, self.workspace_root, self.upload_root, self.task_root]:
            path.mkdir(parents=True, exist_ok=True)


# 全局路径实例
_paths: Optional[AppPaths] = None


def get_paths() -> AppPaths:
    """获取路径管理实例（单例模式）"""
    global _paths
    if _paths is None:
        _paths = AppPaths()
    return _paths
