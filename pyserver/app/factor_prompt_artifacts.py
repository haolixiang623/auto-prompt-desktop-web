from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PREVIEW_TEMPLATE = """# 角色与核心指令
你是一个高精度的文本提取器。你的唯一任务是从用户提供的材料中，逐字逐句地定位并返回指定的要素文本内容。

# 识别要素列表及规则
$(factors)
"""


def compose_factor_prompt(rule_text: str, format_text: str = "") -> str:
    rule = str(rule_text or "").strip()
    fmt = str(format_text or "").strip()
    if rule and fmt:
        return f"{rule}，{fmt}"
    return rule or fmt


def build_factor_lines(factors: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, factor in enumerate(factors, start=1):
        name = str(factor.get("factorname") or factor.get("name") or "").strip()
        prompt = str(
            factor.get("factor_prompt")
            or compose_factor_prompt(factor.get("rule", ""), factor.get("format", ""))
        ).strip()
        if not name:
            continue
        lines.append(f"## {index}.{name}")
        lines.append(prompt)
    return "\n".join(lines)


def build_preview_prompt(prompt_template: str, factors: list[dict[str, Any]]) -> str:
    template = str(prompt_template or "").strip() or DEFAULT_PREVIEW_TEMPLATE
    factor_lines = build_factor_lines(factors)
    if "$(factors)" not in template:
        return template.rstrip() + "\n" + factor_lines
    return template.replace("$(factors)", factor_lines)


def normalize_factor_prompt_artifact(data: Any) -> dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    template_obj = payload.get("template")
    if isinstance(template_obj, dict):
        prompt_template = str(template_obj.get("prompt_template") or "").strip()
    else:
        prompt_template = str(payload.get("prompt_template") or "").strip()
    normalized_factors: list[dict[str, Any]] = []
    for index, raw_factor in enumerate(payload.get("factors") or [], start=1):
        factor = raw_factor if isinstance(raw_factor, dict) else {}
        normalized_factors.append(
            {
                "index": int(factor.get("index") or index),
                "factorname": str(factor.get("factorname") or factor.get("name") or "").strip(),
                "factortype": str(factor.get("factortype") or "1").strip() or "1",
                "factoruse": str(factor.get("factoruse") or factor.get("extract_desc") or "").strip(),
                "factor_prompt": str(
                    factor.get("factor_prompt")
                    or compose_factor_prompt(factor.get("rule", ""), factor.get("format", ""))
                ).strip(),
                "source": str(factor.get("source") or "manual").strip() or "manual",
            }
        )
    return {
        "version": str(payload.get("version") or "1"),
        "carriername": str(payload.get("carriername") or "").strip(),
        "template": {"prompt_template": prompt_template},
        "meta": payload.get("meta") if isinstance(payload.get("meta"), dict) else {},
        "factors": normalized_factors,
    }


def load_factor_prompt_artifact(path: Path | str) -> dict[str, Any]:
    artifact_path = Path(path)
    return normalize_factor_prompt_artifact(json.loads(artifact_path.read_text(encoding="utf-8")))


def save_factor_prompt_artifact(path: Path | str, data: Any) -> dict[str, Any]:
    artifact_path = Path(path)
    normalized = normalize_factor_prompt_artifact(data)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized
