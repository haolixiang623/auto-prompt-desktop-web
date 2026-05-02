from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_REVIEW_RULE_BUILTIN_VARIABLES = [
    {
        "id": "current_date",
        "name": "当前日期",
        "token": "当前日期",
        "placeholder": "$系统变量:当前日期$",
        "dataType": "date",
        "description": "当前系统日期",
    }
]


def _load_json(path: Path | None, default: Any) -> Any:
    if path is None or not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _slugify_token(token: str) -> str:
    slug = re.sub(r"[^\w]+", "_", str(token or "").strip().lower()).strip("_")
    return slug or "builtin_variable"


def normalize_review_rule_builtin_variable(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = {"token": raw}
    item = raw if isinstance(raw, dict) else {}
    token = str(item.get("token") or item.get("name") or "").strip()
    if not token:
        token = DEFAULT_REVIEW_RULE_BUILTIN_VARIABLES[0]["token"]
    name = str(item.get("name") or token).strip() or token
    data_type = str(item.get("dataType") or item.get("type") or "string").strip() or "string"
    placeholder = str(item.get("placeholder") or f"$系统变量:{name}$").strip() or f"$系统变量:{name}$"
    description = str(item.get("description") or "").strip()
    return {
        "id": str(item.get("id") or _slugify_token(token)).strip() or _slugify_token(token),
        "name": name,
        "token": token,
        "placeholder": placeholder,
        "dataType": data_type,
        "description": description,
    }


def normalize_review_rule_builtin_variables(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raw = DEFAULT_REVIEW_RULE_BUILTIN_VARIABLES
    normalized = [normalize_review_rule_builtin_variable(item) for item in raw]
    deduped: list[dict[str, Any]] = []
    seen_tokens: set[str] = set()
    for item in normalized:
        token = item["token"]
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        deduped.append(item)
    return deduped or [normalize_review_rule_builtin_variable(DEFAULT_REVIEW_RULE_BUILTIN_VARIABLES[0])]


def load_review_rule_builtin_variables(paths: Any) -> list[dict[str, Any]]:
    if paths is None:
        return normalize_review_rule_builtin_variables(None)

    settings_path = getattr(paths, "settings_path", None)
    if settings_path is None and getattr(paths, "data_dir", None) is not None:
        settings_path = Path(paths.data_dir) / "settings.json"

    project_path = getattr(paths, "project_config_path", None)
    if project_path is None and getattr(paths, "repo_root", None) is not None:
        project_path = Path(paths.repo_root) / "auto-prompt.project.json"

    local = _load_json(Path(settings_path), {}) if settings_path else {}
    project = _load_json(Path(project_path), {}) if project_path else {}
    raw = local.get("review_rule_builtin_variables")
    if raw is None:
        raw = project.get("review_rule_builtin_variables")
    return normalize_review_rule_builtin_variables(raw)


def map_review_rule_builtin_variables_by_token(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        item["token"]: item
        for item in normalize_review_rule_builtin_variables(items)
    }
