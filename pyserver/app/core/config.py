# 配置管理模块 - 对应 Rust config.rs
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DefaultGodPrompts:
    """默认God Prompt配置"""
    extract: str = ""
    aggregate: str = ""
    review: str = ""
    classify: str = ""


@dataclass
class AppSettings:
    """应用设置"""
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    default_prompts: DefaultGodPrompts = field(default_factory=DefaultGodPrompts)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        prompts = data.pop("default_prompts", {})
        return cls(
            **data,
            default_prompts=DefaultGodPrompts(**prompts)
        )


class SettingsStore:
    """设置存储管理"""
    
    def __init__(self, settings_path: Path, project_config_path: Optional[Path] = None):
        self.settings_path = settings_path
        self.project_config_path = project_config_path
        self._settings = self._load_settings()
    
    def _load_settings(self) -> AppSettings:
        """从文件加载设置"""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return AppSettings.from_dict(data)
            except Exception:
                pass
        return AppSettings()
    
    def save(self) -> None:
        """保存设置到文件"""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self._settings.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get(self) -> AppSettings:
        """获取当前设置"""
        return self._settings
    
    def update(self, settings: AppSettings) -> None:
        """更新设置"""
        self._settings = settings
        self.save()
    
    def migrate_legacy_if_needed(self) -> bool:
        """迁移旧版本配置（如果存在）"""
        # 简化实现，实际项目中可能需要更复杂的迁移逻辑
        return False


def params_to_json(params: Any) -> Dict[str, Any]:
    """将参数转换为JSON字典"""
    if isinstance(params, dict):
        return params
    if hasattr(params, "__dataclass_fields__"):
        return asdict(params)
    return {}
