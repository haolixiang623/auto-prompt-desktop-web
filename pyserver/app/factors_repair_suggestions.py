from __future__ import annotations

import inspect
import re
import shutil
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Awaitable, Callable

from .workspace_validation import MEDIA_EXTENSIONS


FACTOR_HEADER_ALIASES = ("要素字段名称", "要素名称")
CARRY_FORWARD_HEADER_PATTERNS = ("事项名称", "材料名称")
FACTOR_MATCH_THRESHOLD = 0.58
BUILTIN_MATCH_THRESHOLD = 0.72
WORKSPACE_MATERIAL_MATCH_THRESHOLD = 0.72

COMMON_FACTOR_ALIASES = {
    "车牌照号": "号牌号码",
    "车牌照号码": "号牌号码",
    "车牌号码": "号牌号码",
    "车牌号": "号牌号码",
    "牌照号": "号牌号码",
    "牌照号码": "号牌号码",
}

PLACEHOLDER_PATTERN = re.compile(r"#([^#\n]+)#")
FACTOR_PLACEHOLDER_PATTERN = re.compile(r"#([^#\n-]+)-([^#\n]+)#")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _header_index(headers: list[str], aliases: tuple[str, ...]) -> int:
    for alias in aliases:
        for index, header in enumerate(headers):
            if header == alias or alias in header:
                return index
    return -1


def _normalize_row_values(values: Any, size: int) -> list[str]:
    normalized = [_text(item) for item in (values if isinstance(values, list) else [])]
    while len(normalized) < size:
        normalized.append("")
    return normalized[:size]


def _normalize_factor_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    for source, target in COMMON_FACTOR_ALIASES.items():
        text = text.replace(source, target)
    text = (
        text.replace("（", "(")
        .replace("）", ")")
        .replace("【", "[")
        .replace("】", "]")
        .replace("：", ":")
        .replace("／", "/")
        .replace("　", " ")
        .lower()
    )
    text = re.sub(r"[\s\-_/\\:,.，。;；、()\[\]{}<>《》]+", "", text)
    return text


def _similarity(left: Any, right: Any) -> float:
    normalized_left = _normalize_factor_name(left)
    normalized_right = _normalize_factor_name(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return 0.86
    ordered = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    unordered = SequenceMatcher(None, "".join(sorted(normalized_left)), "".join(sorted(normalized_right))).ratio()
    return max(ordered, unordered * 0.92)


def _best_match(target: str, candidates: list[str]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for candidate in candidates:
        score = _similarity(target, candidate)
        if best is None or score > best["score"]:
            best = {"value": candidate, "score": round(score, 4)}
    return best


def _build_snapshot(headers: list[Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    width = max(
        len(headers) if isinstance(headers, list) else 0,
        *(len(row.get("values") or []) for row in (rows or [])),
        1,
    )
    normalized_headers = _normalize_row_values(headers, width)
    material_idx = _header_index(normalized_headers, ("材料名称",))
    factor_idx = _header_index(normalized_headers, FACTOR_HEADER_ALIASES)
    keypoint_idx = _header_index(normalized_headers, ("审查要点名称",))
    rule_desc_idx = _header_index(normalized_headers, ("审查要点规则说明",))

    normalized_rows: list[dict[str, Any]] = []
    rows_by_number: dict[int, dict[str, Any]] = {}
    factor_names_by_material: dict[str, list[str]] = defaultdict(list)
    factor_rows_by_material: dict[str, list[dict[str, Any]]] = defaultdict(list)
    last_row_by_material: dict[str, dict[str, Any]] = {}
    factors_seen: dict[str, set[str]] = defaultdict(set)
    max_row_number = 1

    for source_row in rows or []:
        row_number = source_row.get("rowNumber")
        parsed_row_number = int(row_number) if isinstance(row_number, int) or str(row_number).isdigit() else None
        normalized_row = {
            **(source_row or {}),
            "rowNumber": parsed_row_number,
            "values": _normalize_row_values(source_row.get("values") if isinstance(source_row, dict) else [], width),
        }
        normalized_rows.append(normalized_row)

        if parsed_row_number is not None:
            rows_by_number[parsed_row_number] = normalized_row
            max_row_number = max(max_row_number, parsed_row_number)

        material_name = normalized_row["values"][material_idx] if material_idx >= 0 else ""
        factor_name = normalized_row["values"][factor_idx] if factor_idx >= 0 else ""
        if material_name:
            last_row_by_material[material_name] = normalized_row
        if material_name and factor_name:
            factor_rows_by_material[material_name].append(normalized_row)
        if material_name and factor_name and factor_name not in factors_seen[material_name]:
            factors_seen[material_name].add(factor_name)
            factor_names_by_material[material_name].append(factor_name)

    return {
        "headers": normalized_headers,
        "rows": normalized_rows,
        "rows_by_number": rows_by_number,
        "width": width,
        "material_idx": material_idx,
        "factor_idx": factor_idx,
        "keypoint_idx": keypoint_idx,
        "rule_desc_idx": rule_desc_idx,
        "factor_names_by_material": factor_names_by_material,
        "factor_rows_by_material": factor_rows_by_material,
        "last_row_by_material": last_row_by_material,
        "max_row_number": max_row_number,
    }


def _row_material_name(snapshot: dict[str, Any], row: dict[str, Any] | None) -> str:
    material_idx = snapshot["material_idx"]
    if material_idx < 0 or not row:
        return ""
    return _text(row["values"][material_idx])


def _row_factor_name(snapshot: dict[str, Any], row: dict[str, Any] | None) -> str:
    factor_idx = snapshot["factor_idx"]
    if factor_idx < 0 or not row:
        return ""
    return _text(row["values"][factor_idx])


def _row_keypoint_name(snapshot: dict[str, Any], row: dict[str, Any] | None) -> str:
    keypoint_idx = snapshot["keypoint_idx"]
    if keypoint_idx < 0 or not row:
        return ""
    return _text(row["values"][keypoint_idx])


def _row_rule_description(snapshot: dict[str, Any], row: dict[str, Any] | None) -> str:
    rule_desc_idx = snapshot["rule_desc_idx"]
    if rule_desc_idx < 0 or not row:
        return ""
    return _text(row["values"][rule_desc_idx])


def _replace_placeholder(rule_text: str, old_token: str, new_token: str) -> str:
    return str(rule_text or "").replace(f"#{old_token}#", f"#{new_token}#")


def _extract_factor_placeholders(rule_text: Any) -> list[dict[str, str]]:
    return [
        {
            "token": f"{match.group(1).strip()}-{match.group(2).strip()}",
            "material": match.group(1).strip(),
            "factor": match.group(2).strip(),
        }
        for match in FACTOR_PLACEHOLDER_PATTERN.finditer(str(rule_text or ""))
    ]


def _build_insert_row_values(snapshot: dict[str, Any], material_name: str, factor_name: str) -> list[str]:
    values = [""] * snapshot["width"]
    factor_idx = snapshot["factor_idx"]
    material_idx = snapshot["material_idx"]
    template_row = snapshot["last_row_by_material"].get(material_name)

    for column_index, header in enumerate(snapshot["headers"]):
        if factor_idx >= 0 and column_index == factor_idx:
            values[column_index] = factor_name
            continue
        if material_idx >= 0 and column_index == material_idx:
            values[column_index] = material_name
            continue
        if any(pattern in header for pattern in CARRY_FORWARD_HEADER_PATTERNS):
            values[column_index] = template_row["values"][column_index] if template_row else ""
    return values


def _clone_factor_row_values(snapshot: dict[str, Any], source_row: dict[str, Any], material_name: str) -> list[str]:
    values = _normalize_row_values(source_row.get("values"), snapshot["width"])
    material_idx = snapshot["material_idx"]
    keypoint_idx = snapshot["keypoint_idx"]
    rule_desc_idx = snapshot["rule_desc_idx"]
    if material_idx >= 0:
        values[material_idx] = material_name
    if keypoint_idx >= 0:
        values[keypoint_idx] = ""
    if rule_desc_idx >= 0:
        values[rule_desc_idx] = ""
    return values


def _last_material_row_number(snapshot: dict[str, Any], material_name: str) -> int | None:
    row = snapshot["last_row_by_material"].get(material_name)
    if not row:
        return None
    row_number = row.get("rowNumber")
    return row_number if isinstance(row_number, int) else None


def _find_factor_from_keypoint(keypoint_name: str, candidates: list[str]) -> str:
    if not keypoint_name:
        return ""
    for candidate in candidates:
        if candidate and candidate in keypoint_name:
            return candidate
    best = _best_match(keypoint_name, candidates)
    if best and best["score"] >= FACTOR_MATCH_THRESHOLD:
        return str(best["value"])
    return ""


async def _maybe_call_llm(
    llm_rule_description_suggester: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None] | dict[str, Any] | None] | None,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    if llm_rule_description_suggester is None:
        return None
    result = llm_rule_description_suggester(context)
    if inspect.isawaitable(result):
        return await result
    return result


def _base_item(diagnostic: dict[str, Any], index: int, *, title: str, summary: str) -> dict[str, Any]:
    diagnostic_id = _text(diagnostic.get("id") or diagnostic.get("diagnosticId") or f"diagnostic-{index}")
    return {
        "id": f"repair-suggestion-{index}",
        "diagnosticId": diagnostic_id,
        "issueCode": _text(diagnostic.get("code")),
        "title": title,
        "summary": summary,
        "requiresConfirmation": True,
        "usedLlm": False,
        "confidence": 0.0,
        "reason": "",
        "status": "unsupported",
        "patches": [],
    }


def _unsupported_item(diagnostic: dict[str, Any], index: int, *, title: str, summary: str, reason: str) -> dict[str, Any]:
    item = _base_item(diagnostic, index, title=title, summary=summary)
    item["reason"] = reason
    return item


def _suggested_item(
    diagnostic: dict[str, Any],
    index: int,
    *,
    title: str,
    summary: str,
    reason: str,
    confidence: float,
    patches: list[dict[str, Any]],
    used_llm: bool = False,
) -> dict[str, Any]:
    item = _base_item(diagnostic, index, title=title, summary=summary)
    item["status"] = "suggested"
    item["reason"] = reason
    item["confidence"] = round(float(confidence), 2)
    item["patches"] = patches
    item["usedLlm"] = used_llm
    return item


def _suggest_missing_referenced_factor(diagnostic: dict[str, Any], index: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    ref_material = _text(diagnostic.get("materialName"))
    ref_factor = _text(diagnostic.get("factorName"))
    row_number = int(diagnostic.get("row") or 0)
    token = _text(diagnostic.get("token") or (f"{ref_material}-{ref_factor}" if ref_material and ref_factor else ""))
    row = snapshot["rows_by_number"].get(row_number)
    rule_desc_idx = snapshot["rule_desc_idx"]
    rule_text = _row_rule_description(snapshot, row)
    summary = f"第 {row_number} 行缺少引用要素“{ref_material}-{ref_factor}”"

    if not row or rule_desc_idx < 0 or not ref_material or not ref_factor:
        return _unsupported_item(
            diagnostic,
            index,
            title="补充缺失要素引用",
            summary=summary,
            reason="当前草稿中缺少定位信息，暂时无法生成可执行建议。",
        )

    candidates = list(snapshot["factor_names_by_material"].get(ref_material, []))
    best = _best_match(ref_factor, candidates)
    if best and best["score"] >= FACTOR_MATCH_THRESHOLD:
        next_token = f"{ref_material}-{best['value']}"
        after_text = _replace_placeholder(rule_text, token, next_token)
        if after_text != rule_text:
            return _suggested_item(
                diagnostic,
                index,
                title="将规则引用修正为已存在要素",
                summary=f"把 #{token}# 修正为 #{next_token}#",
                reason=f"已在材料“{ref_material}”下模糊匹配到最接近的要素“{best['value']}”。",
                confidence=best["score"],
                patches=[
                    {
                        "type": "cell_update",
                        "rowNumber": row_number,
                        "columnIndex": rule_desc_idx,
                        "before": rule_text,
                        "after": after_text,
                    }
                ],
            )

    insert_after_row = _last_material_row_number(snapshot, ref_material)
    if insert_after_row is None:
        return _unsupported_item(
            diagnostic,
            index,
            title="新增缺失要素定义",
            summary=summary,
            reason=f"材料“{ref_material}”当前不在草稿中，无法安全生成新增行建议。",
        )

    return _suggested_item(
        diagnostic,
        index,
        title="新增缺失要素定义",
        summary=f"在材料“{ref_material}”下新增要素“{ref_factor}”定义行",
        reason=f"未找到可安全替换的近似要素，建议先补一行要素定义，再由你确认后保存。",
        confidence=0.66,
        patches=[
            {
                "type": "row_insert",
                "afterRowNumber": insert_after_row,
                "focusColumnIndex": snapshot["factor_idx"] if snapshot["factor_idx"] >= 0 else 0,
                "rowValues": _build_insert_row_values(snapshot, ref_material, ref_factor),
            }
        ],
    )


def _suggest_missing_referenced_material(diagnostic: dict[str, Any], index: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    ref_material = _text(diagnostic.get("materialName"))
    row_number = int(diagnostic.get("row") or 0)
    row = snapshot["rows_by_number"].get(row_number)
    rule_desc_idx = snapshot["rule_desc_idx"]
    rule_text = _row_rule_description(snapshot, row)
    summary = f"第 {row_number} 行引用材料“{ref_material}”不存在对应要素定义"

    if not row or rule_desc_idx < 0 or not ref_material:
        return _unsupported_item(
            diagnostic,
            index,
            title="修正引用材料名称",
            summary=summary,
            reason="当前草稿中缺少足够的定位信息，暂时无法生成可执行修复。",
        )

    material_candidates = list(snapshot["factor_names_by_material"].keys())
    best_material = _best_match(ref_material, material_candidates)
    if not best_material or best_material["score"] < FACTOR_MATCH_THRESHOLD:
        return _unsupported_item(
            diagnostic,
            index,
            title="修正引用材料名称",
            summary=summary,
            reason="暂未找到足够接近的已有材料名称，建议人工检查目录和材料定义是否一致。",
        )

    next_material = str(best_material["value"])
    placeholders = [
        item
        for item in _extract_factor_placeholders(rule_text)
        if item["material"] == ref_material or _similarity(item["material"], ref_material) >= 0.9
    ]
    if not placeholders:
        return _unsupported_item(
            diagnostic,
            index,
            title="修正引用材料名称",
            summary=summary,
            reason="未在当前规则说明中找到可直接替换的材料引用占位符。",
        )

    next_rule_text = str(rule_text or "")
    corrected_factor = False
    for placeholder in placeholders:
        next_factor = placeholder["factor"]
        candidate_factors = list(snapshot["factor_names_by_material"].get(next_material, []))
        if next_factor not in candidate_factors:
            best_factor = _best_match(next_factor, candidate_factors)
            if best_factor and best_factor["score"] >= FACTOR_MATCH_THRESHOLD:
                next_factor = str(best_factor["value"])
                corrected_factor = True
        next_rule_text = _replace_placeholder(
            next_rule_text,
            placeholder["token"],
            f"{next_material}-{next_factor}",
        )

    if next_rule_text == rule_text:
        return _unsupported_item(
            diagnostic,
            index,
            title="修正引用材料名称",
            summary=summary,
            reason="已找到候选材料，但没有形成实际可替换的修复结果。",
        )

    reason = f"已将引用材料从“{ref_material}”模糊匹配为已存在材料“{next_material}”。"
    if corrected_factor:
        reason += " 同时按该材料下的现有要素定义纠正了关联要素名称。"
    return _suggested_item(
        diagnostic,
        index,
        title="修正引用材料名称",
        summary=f"把规则里的材料引用修正为“{next_material}”",
        reason=reason,
        confidence=best_material["score"],
        patches=[
            {
                "type": "cell_update",
                "rowNumber": row_number,
                "columnIndex": rule_desc_idx,
                "before": rule_text,
                "after": next_rule_text,
            }
        ],
    )


def _suggest_missing_factor_definition_for_material(diagnostic: dict[str, Any], index: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    material_name = _text(diagnostic.get("materialName"))
    summary = f"材料“{material_name}”在工作区中有附件，但 factors.xlsx 中没有对应要素定义"

    if not material_name or snapshot["factor_idx"] < 0:
        return _unsupported_item(
            diagnostic,
            index,
            title="补齐材料要素定义",
            summary=summary,
            reason="当前草稿缺少足够的材料或要素列信息，暂时无法生成新增建议。",
        )

    material_candidates = [
        name
        for name in snapshot["factor_names_by_material"].keys()
        if name and name != material_name
    ]
    best_material = _best_match(material_name, material_candidates)
    if not best_material or best_material["score"] < FACTOR_MATCH_THRESHOLD:
        return _unsupported_item(
            diagnostic,
            index,
            title="补齐材料要素定义",
            summary=summary,
            reason="暂未匹配到足够接近的已定义材料，建议人工补充该材料的要素定义。",
        )

    source_material = str(best_material["value"])
    source_rows = list(snapshot["factor_rows_by_material"].get(source_material, []))
    if not source_rows:
        return _unsupported_item(
            diagnostic,
            index,
            title="补齐材料要素定义",
            summary=summary,
            reason=f"已找到相近材料“{source_material}”，但它本身没有可复制的要素定义行。",
        )

    patches: list[dict[str, Any]] = []
    anchor_row_number = int(snapshot.get("max_row_number") or 1)
    focus_column_index = snapshot["factor_idx"] if snapshot["factor_idx"] >= 0 else 0
    for source_row in source_rows:
        patches.append(
            {
                "type": "row_insert",
                "afterRowNumber": anchor_row_number,
                "focusColumnIndex": focus_column_index,
                "rowValues": _clone_factor_row_values(snapshot, source_row, material_name),
            }
        )
        anchor_row_number += 1

    return _suggested_item(
        diagnostic,
        index,
        title="补齐材料要素定义",
        summary=f"按相近材料“{source_material}”复制 {len(source_rows)} 行要素定义到“{material_name}”",
        reason=f"已找到最接近的已定义材料“{source_material}”，建议先复制其要素定义作为起点，再由你人工确认后保存。",
        confidence=best_material["score"],
        patches=patches,
    )


def _suggest_missing_material_directory(
    diagnostic: dict[str, Any],
    index: int,
    snapshot: dict[str, Any],
    workspace_materials: list[dict[str, Any]],
) -> dict[str, Any]:
    material_name = _text(diagnostic.get("materialName"))
    summary = f"材料“{material_name}”在 factors.xlsx 中存在要素定义，但工作区缺少可用材料目录"

    if not material_name:
        return _unsupported_item(
            diagnostic,
            index,
            title="补齐材料目录",
            summary=summary,
            reason="当前问题缺少材料名称，暂时无法生成目录修复建议。",
        )

    candidates = [
        item
        for item in (workspace_materials or [])
        if _text(item.get("name")) and _text(item.get("name")) != material_name
    ]
    candidates_with_factors = [
        item
        for item in candidates
        if _text(item.get("name")) in snapshot["factor_names_by_material"]
    ]
    candidate_pool = candidates_with_factors or candidates
    best_match: dict[str, Any] | None = None
    for item in candidate_pool:
        score = _similarity(material_name, item.get("name"))
        if best_match is None or score > best_match["score"]:
            best_match = {
                "name": _text(item.get("name")),
                "score": round(score, 4),
                "image_count": int(item.get("image_count") or 0),
            }

    if not best_match or best_match["score"] < WORKSPACE_MATERIAL_MATCH_THRESHOLD:
        return _unsupported_item(
            diagnostic,
            index,
            title="补齐材料目录",
            summary=summary,
            reason="暂未匹配到足够接近的已有材料目录，建议人工补充目录或样本附件后重新校验。",
        )

    return _suggested_item(
        diagnostic,
        index,
        title="补齐材料目录",
        summary=f"为“{material_name}”创建目录，并复制“{best_match['name']}”的附件样本",
        reason=f"已将缺失目录模糊匹配到现有材料“{best_match['name']}”，建议先复制其 {best_match['image_count']} 个附件样本作为修复起点。",
        confidence=best_match["score"],
        patches=[
            {
                "type": "workspace_material_clone",
                "sourceMaterialName": best_match["name"],
                "targetMaterialName": material_name,
                "sourceFileCount": best_match["image_count"],
            }
        ],
    )


def _suggest_invalid_placeholder(
    diagnostic: dict[str, Any],
    index: int,
    snapshot: dict[str, Any],
    builtin_variables: list[dict[str, Any]],
) -> dict[str, Any]:
    row_number = int(diagnostic.get("row") or 0)
    token = _text(diagnostic.get("token"))
    row = snapshot["rows_by_number"].get(row_number)
    rule_desc_idx = snapshot["rule_desc_idx"]
    rule_text = _row_rule_description(snapshot, row)
    material_name = _row_material_name(snapshot, row) or _text(diagnostic.get("materialName"))
    factor_candidates = list(snapshot["factor_names_by_material"].get(material_name, []))
    builtin_tokens = [_text(item.get("token")) for item in builtin_variables if _text(item.get("token"))]
    summary = f"第 {row_number} 行占位符 #{token}# 无法识别"

    if not row or rule_desc_idx < 0 or not token:
        return _unsupported_item(
            diagnostic,
            index,
            title="修正无效占位符",
            summary=summary,
            reason="当前草稿中缺少足够的占位符上下文，暂时无法生成替换建议。",
        )

    best_factor = _best_match(token, factor_candidates)
    best_builtin = _best_match(token, builtin_tokens)

    if best_factor and best_factor["score"] >= FACTOR_MATCH_THRESHOLD and (
        not best_builtin or best_factor["score"] >= best_builtin["score"]
    ):
        replacement = str(best_factor["value"])
        after_text = _replace_placeholder(rule_text, token, replacement)
        if after_text != rule_text:
            return _suggested_item(
                diagnostic,
                index,
                title="按当前材料要素简写修正占位符",
                summary=f"把 #{token}# 修正为 #{replacement}#",
                reason=f"该占位符更像当前材料“{material_name}”下的要素简写，最接近“{replacement}”。",
                confidence=best_factor["score"],
                patches=[
                    {
                        "type": "cell_update",
                        "rowNumber": row_number,
                        "columnIndex": rule_desc_idx,
                        "before": rule_text,
                        "after": after_text,
                    }
                ],
            )

    if best_builtin and best_builtin["score"] >= BUILTIN_MATCH_THRESHOLD:
        replacement = str(best_builtin["value"])
        after_text = _replace_placeholder(rule_text, token, replacement)
        if after_text != rule_text:
            return _suggested_item(
                diagnostic,
                index,
                title="按内置变量修正占位符",
                summary=f"把 #{token}# 修正为 #{replacement}#",
                reason=f"该占位符更像已维护的内置变量“{replacement}”，建议按内置变量名称修正。",
                confidence=best_builtin["score"],
                patches=[
                    {
                        "type": "cell_update",
                        "rowNumber": row_number,
                        "columnIndex": rule_desc_idx,
                        "before": rule_text,
                        "after": after_text,
                    }
                ],
            )

    return _unsupported_item(
        diagnostic,
        index,
        title="修正无效占位符",
        summary=summary,
        reason="暂未匹配到足够可靠的要素或内置变量候选，建议人工检查占位符语义。",
    )


async def _suggest_empty_rule_description(
    diagnostic: dict[str, Any],
    index: int,
    snapshot: dict[str, Any],
    builtin_variables: list[dict[str, Any]],
    llm_rule_description_suggester: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None] | dict[str, Any] | None] | None,
) -> dict[str, Any]:
    row_number = int(diagnostic.get("row") or 0)
    row = snapshot["rows_by_number"].get(row_number)
    rule_desc_idx = snapshot["rule_desc_idx"]
    material_name = _row_material_name(snapshot, row) or _text(diagnostic.get("materialName"))
    keypoint_name = _row_keypoint_name(snapshot, row) or _text(diagnostic.get("keypointName"))
    factor_candidates = list(snapshot["factor_names_by_material"].get(material_name, []))
    factor_name = _row_factor_name(snapshot, row) or _find_factor_from_keypoint(keypoint_name, factor_candidates)
    summary = f"第 {row_number} 行审查要点规则说明为空"

    if not row or rule_desc_idx < 0:
        return _unsupported_item(
            diagnostic,
            index,
            title="补充规则说明",
            summary=summary,
            reason="当前草稿中缺少可定位行，暂时无法生成候选规则说明。",
        )

    context = {
        "rowNumber": row_number,
        "materialName": material_name,
        "keypointName": keypoint_name,
        "factorName": factor_name,
        "factorCandidates": factor_candidates,
        "builtinVariableTokens": [_text(item.get("token")) for item in builtin_variables if _text(item.get("token"))],
        "headers": snapshot["headers"],
        "rowValues": list(row["values"]),
    }
    try:
        llm_result = await _maybe_call_llm(llm_rule_description_suggester, context)
    except Exception:
        llm_result = None

    llm_content = _text((llm_result or {}).get("content"))
    if llm_content:
        return _suggested_item(
            diagnostic,
            index,
            title="补充规则说明候选",
            summary=f"为第 {row_number} 行生成可确认的规则说明候选",
            reason=_text((llm_result or {}).get("reason")) or "已结合当前材料、要素和审查要点名称生成候选规则说明。",
            confidence=float((llm_result or {}).get("confidence") or 0.7),
            used_llm=True,
            patches=[
                {
                    "type": "cell_update",
                    "rowNumber": row_number,
                    "columnIndex": rule_desc_idx,
                    "before": _row_rule_description(snapshot, row),
                    "after": llm_content,
                }
            ],
        )

    if factor_name and keypoint_name:
        heuristic_text = f"#{factor_name}#需满足“{keypoint_name}”要求"
    elif factor_name:
        heuristic_text = f"#{factor_name}#不能为空，并需满足审查要求"
    elif keypoint_name:
        heuristic_text = f"请围绕“{keypoint_name}”补充明确的审查规则说明"
    else:
        heuristic_text = ""

    if heuristic_text:
        return _suggested_item(
            diagnostic,
            index,
            title="补充规则说明候选",
            summary=f"为第 {row_number} 行补一个可继续编辑的规则说明草案",
            reason="当前未启用模型建议，已基于材料与审查要点名称生成一个低风险草案，仍需你确认后保存。",
            confidence=0.31,
            patches=[
                {
                    "type": "cell_update",
                    "rowNumber": row_number,
                    "columnIndex": rule_desc_idx,
                    "before": _row_rule_description(snapshot, row),
                    "after": heuristic_text,
                }
            ],
        )

    return _unsupported_item(
        diagnostic,
        index,
        title="补充规则说明",
        summary=summary,
        reason="缺少足够的材料/要素/审查要点上下文，建议人工填写规则说明。",
    )


def _suggest_duplicate_factor(diagnostic: dict[str, Any], index: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    row_numbers = [int(item) for item in (diagnostic.get("rowNumbers") or []) if str(item).isdigit()]
    material_name = _text(diagnostic.get("materialName"))
    factor_name = _text(diagnostic.get("factorName"))
    summary = f"材料“{material_name}”下要素“{factor_name}”存在重复定义"
    if len(row_numbers) < 2:
        return _unsupported_item(
            diagnostic,
            index,
            title="删除重复要素行",
            summary=summary,
            reason="重复行信息不足，暂时无法生成删除建议。",
        )

    rows = [snapshot["rows_by_number"].get(row_number) for row_number in row_numbers]
    if any(row is None for row in rows):
        return _unsupported_item(
            diagnostic,
            index,
            title="删除重复要素行",
            summary=summary,
            reason="重复行在当前草稿中未全部找到，建议人工核对后处理。",
        )

    normalized_rows = [tuple(_normalize_row_values(row["values"], snapshot["width"])) for row in rows if row]
    if len(set(normalized_rows)) != 1:
        return _unsupported_item(
            diagnostic,
            index,
            title="删除重复要素行",
            summary=summary,
            reason="这些重复要素行内容并不完全一致，自动删除风险较高，建议人工甄别后处理。",
        )

    patches = [{"type": "row_delete", "rowNumber": row_number} for row_number in row_numbers[1:]]
    return _suggested_item(
        diagnostic,
        index,
        title="删除重复要素行",
        summary=f"保留第 {row_numbers[0]} 行，删除后续重复行",
        reason="重复要素行内容完全一致，适合先给出人工确认后的删除建议。",
        confidence=0.95,
        patches=patches,
    )


async def generate_factors_repair_suggestions(
    *,
    headers: list[Any],
    rows: list[dict[str, Any]],
    merged_ranges: list[dict[str, Any]] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    builtin_variables: list[dict[str, Any]] | None = None,
    workspace_materials: list[dict[str, Any]] | None = None,
    llm_rule_description_suggester: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None] | dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    del merged_ranges
    snapshot = _build_snapshot(headers or [], rows or [])
    builtin_variables = builtin_variables or []
    workspace_materials = workspace_materials or []
    items: list[dict[str, Any]] = []

    for index, diagnostic in enumerate(diagnostics or [], start=1):
        code = _text((diagnostic or {}).get("code"))
        if code == "missing_referenced_factor":
            item = _suggest_missing_referenced_factor(diagnostic, index, snapshot)
        elif code == "missing_referenced_material":
            item = _suggest_missing_referenced_material(diagnostic, index, snapshot)
        elif code in {"missing_factor_definition_for_material", "selected_material_missing_factors"}:
            item = _suggest_missing_factor_definition_for_material(diagnostic, index, snapshot)
        elif code in {"missing_material_directory", "selected_material_missing_directory"}:
            item = _suggest_missing_material_directory(diagnostic, index, snapshot, workspace_materials)
        elif code == "invalid_placeholder":
            item = _suggest_invalid_placeholder(diagnostic, index, snapshot, builtin_variables)
        elif code == "empty_rule_description":
            item = await _suggest_empty_rule_description(
                diagnostic,
                index,
                snapshot,
                builtin_variables,
                llm_rule_description_suggester,
            )
        elif code == "duplicate_factor":
            item = _suggest_duplicate_factor(diagnostic, index, snapshot)
        else:
            item = _unsupported_item(
                diagnostic,
                index,
                title="暂不支持自动建议",
                summary=_text(diagnostic.get("message")) or "当前问题暂不支持自动建议",
                reason="这一类问题更适合先人工检查目录、列结构或原始数据，再继续修复。",
            )
        items.append(item)

    suggested = sum(1 for item in items if item["status"] == "suggested")
    unsupported = sum(1 for item in items if item["status"] != "suggested")
    llm_used = sum(1 for item in items if item.get("usedLlm"))

    return {
        "items": items,
        "stats": {
            "total": len(items),
            "suggested": suggested,
            "unsupported": unsupported,
            "llmUsed": llm_used,
        },
    }


def _safe_material_name(value: Any) -> str:
    material_name = _text(value)
    if not material_name or material_name in {".", ".."} or "/" in material_name or "\\" in material_name:
        raise ValueError("材料目录名称不合法。")
    return material_name


def _list_material_media_files(material_dir: Path) -> list[Path]:
    if not material_dir.exists() or not material_dir.is_dir():
        return []
    return [
        child
        for child in sorted(material_dir.iterdir(), key=lambda item: item.name)
        if child.is_file() and child.suffix.lower() in MEDIA_EXTENSIONS
    ]


def _apply_workspace_material_clone_patch(work_dir: Path, patch: dict[str, Any]) -> dict[str, Any]:
    source_material = _safe_material_name(patch.get("sourceMaterialName"))
    target_material = _safe_material_name(patch.get("targetMaterialName"))
    if source_material == target_material:
        raise ValueError("源材料目录和目标材料目录不能相同。")

    source_dir = work_dir / source_material
    target_dir = work_dir / target_material
    source_files = _list_material_media_files(source_dir)
    if not source_files:
        raise ValueError(f"源材料目录“{source_material}”不存在可复制的附件。")

    target_dir.mkdir(parents=True, exist_ok=True)
    copied_files: list[str] = []
    for source_file in source_files:
        target_file = target_dir / source_file.name
        if target_file.exists():
            if target_file.is_file() and target_file.stat().st_size == source_file.stat().st_size:
                copied_files.append(str(target_file))
                continue
            next_index = 2
            while target_file.exists():
                target_file = target_dir / f"{source_file.stem}-{next_index}{source_file.suffix}"
                next_index += 1
        shutil.copy2(source_file, target_file)
        copied_files.append(str(target_file))

    return {
        "type": "workspace_material_clone",
        "sourceMaterialName": source_material,
        "targetMaterialName": target_material,
        "copiedFiles": copied_files,
    }


def apply_factors_repair_suggestion_patches(*, work_dir: str | Path, patches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    root = Path(work_dir)
    applied: list[dict[str, Any]] = []
    for patch in patches or []:
        patch_type = _text((patch or {}).get("type"))
        if patch_type == "workspace_material_clone":
            applied.append(_apply_workspace_material_clone_patch(root, patch))
            continue
        raise ValueError(f"暂不支持执行该修复动作：{patch_type or 'unknown'}")

    return {
        "count": len(applied),
        "items": applied,
    }
