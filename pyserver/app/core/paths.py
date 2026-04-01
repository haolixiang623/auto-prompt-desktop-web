# 路径管理模块 - 对应 Rust paths.rs
import os
from pathlib import Path
from typing import Optional


class AppPaths:
    """应用程序路径管理"""
    
    def __init__(self):
        # 基础目录
        default_repo_root = Path(__file__).resolve().parents[3]
        self.repo_root = Path(os.environ.get("AUTO_PROMPT_REPO_ROOT", str(default_repo_root)))
        self.skills_dir = Path(os.environ.get("AUTO_PROMPT_SKILLS_DIR", self.repo_root / "skills"))
        self.data_dir = Path(os.environ.get("AUTO_PROMPT_DATA_DIR", self.repo_root / ".runtime-data"))
        
        # 派生路径
        self.workspace_root = self.data_dir / "workspaces"
        self.upload_root = self.data_dir / "uploads"
        self.task_root = self.data_dir / "tasks"
        self.app_db_path = self.data_dir / "app.db"
        self.settings_path = self.data_dir / "settings.json"

        # 用户隔离根目录（user_id 子目录下隔离）
        # - workspaces/{user_id}/：用户上传的材料文件夹
        # - outputs/{user_id}/prompts/：用户生成的提示词 txt
        # - outputs/{user_id}/review_rules/：用户生成的审查规则
        self.user_workspace_root = self.data_dir / "workspaces"
        self.user_output_root = self.data_dir / "outputs"

        # 前端资源路径
        self.web_dist = Path(os.environ.get("AUTO_PROMPT_WEB_DIST", self.repo_root / "dist"))

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保所有必要的目录存在"""
        for path in [self.data_dir, self.workspace_root, self.upload_root,
                     self.task_root, self.user_workspace_root, self.user_output_root]:
            path.mkdir(parents=True, exist_ok=True)


# 全局路径实例
_paths: Optional[AppPaths] = None


def get_paths() -> AppPaths:
    """获取路径管理实例（单例模式）"""
    global _paths
    if _paths is None:
        _paths = AppPaths()
    return _paths
