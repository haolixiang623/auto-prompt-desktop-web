from __future__ import annotations

import re
from typing import Any, Iterable


REVIEW_RULE_FACTOR_REF_PATTERN = re.compile(r"#([^#\n-]+)-([^#\n]+)#")
REVIEW_RULE_PLACEHOLDER_PATTERN = re.compile(r"#([^#\n]+)#")


def normalize_review_rule_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def resolve_review_rule_placeholder_token(
    token: Any,
    *,
    current_material: str = "",
    builtin_variable_map: dict[str, dict[str, Any]] | None = None,
    known_factor_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    normalized_token = normalize_review_rule_token(token)
    builtin_variable_map = builtin_variable_map or {}
    factor_match = re.fullmatch(r"([^#\n-]+)-([^#\n]+)", normalized_token)
    if factor_match:
        return {
            "kind": "factor",
            "token": normalized_token,
            "material": factor_match.group(1).strip(),
            "field": factor_match.group(2).strip(),
            "shorthand": False,
        }

    builtin = builtin_variable_map.get(normalized_token)
    if builtin:
        return {
            "kind": "builtin",
            "token": normalized_token,
            "name": builtin["name"],
            "placeholder": builtin["placeholder"],
            "dataType": builtin["dataType"],
        }

    normalized_factor_names = {
        normalize_review_rule_token(name)
        for name in (known_factor_names or [])
        if normalize_review_rule_token(name)
    }
    if current_material and normalized_token and normalized_token in normalized_factor_names:
        return {
            "kind": "factor",
            "token": normalized_token,
            "material": current_material,
            "field": normalized_token,
            "shorthand": True,
        }

    return {
        "kind": "invalid",
        "token": normalized_token,
    }


def extract_review_rule_placeholders(text: Any) -> list[str]:
    if not text:
        return []
    return [
        normalize_review_rule_token(match.group(1))
        for match in REVIEW_RULE_PLACEHOLDER_PATTERN.finditer(str(text))
    ]


def extract_review_rule_refs(
    text: Any,
    *,
    current_material: str = "",
    builtin_variable_map: dict[str, dict[str, Any]] | None = None,
    known_factor_names: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    if not text:
        return []
    return [
        resolve_review_rule_placeholder_token(
            match.group(1),
            current_material=current_material,
            builtin_variable_map=builtin_variable_map,
            known_factor_names=known_factor_names,
        )
        for match in REVIEW_RULE_PLACEHOLDER_PATTERN.finditer(str(text))
    ]


def replace_review_rule_refs_with_placeholders(
    text: Any,
    *,
    current_material: str = "",
    builtin_variable_map: dict[str, dict[str, Any]] | None = None,
    known_factor_names: Iterable[str] | None = None,
) -> str:
    def _replace(match: re.Match[str]) -> str:
        ref = resolve_review_rule_placeholder_token(
            match.group(1),
            current_material=current_material,
            builtin_variable_map=builtin_variable_map,
            known_factor_names=known_factor_names,
        )
        if ref["kind"] == "factor":
            material = str(ref["material"]).replace("：", ":").strip()
            field = str(ref["field"]).replace("：", ":").strip()
            return f"${material}:{field}$"
        if ref["kind"] == "builtin":
            return ref["placeholder"]
        return match.group(0)

    return REVIEW_RULE_PLACEHOLDER_PATTERN.sub(_replace, str(text or ""))
