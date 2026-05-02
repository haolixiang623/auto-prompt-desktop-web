from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl


DEFAULT_FACTORS_HEADERS = [
    "材料名称",
    "要素字段名称",
    "要素提取说明",
    "审查要点名称",
    "审查要点规则说明",
]


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_values(values: list[Any], size: int) -> list[str]:
    normalized = [_text(value) for value in list(values or [])[:size]]
    if len(normalized) < size:
        normalized.extend([""] * (size - len(normalized)))
    return normalized


def _sheet_dimensions(worksheet: Any) -> tuple[int, list[list[str]]]:
    rows: list[list[str]] = []
    max_non_empty_col = 0
    for row in worksheet.iter_rows(values_only=True):
        values = [_text(value) for value in row]
        last_non_empty_col = 0
        for index, value in enumerate(values, start=1):
            if value:
                last_non_empty_col = index
        max_non_empty_col = max(max_non_empty_col, last_non_empty_col)
        rows.append(values)
    return max_non_empty_col, rows


def _empty_workbook_payload(file_path: Path) -> dict[str, Any]:
    return {
        "filePath": str(file_path),
        "exists": file_path.exists(),
        "sheetName": "Sheet1",
        "headers": list(DEFAULT_FACTORS_HEADERS),
        "rows": [],
        "summary": {
            "columnCount": len(DEFAULT_FACTORS_HEADERS),
            "rowCount": 0,
        },
    }


def load_factors_workbook(file_path: str | Path) -> dict[str, Any]:
    target = Path(file_path)
    if not target.exists():
        return _empty_workbook_payload(target)

    workbook = openpyxl.load_workbook(target)
    try:
        worksheet = workbook.active
        max_non_empty_col, raw_rows = _sheet_dimensions(worksheet)
        if max_non_empty_col <= 0:
            return {
                **_empty_workbook_payload(target),
                "exists": True,
                "sheetName": worksheet.title,
            }

        headers = _normalize_values(raw_rows[0] if raw_rows else [], max_non_empty_col)
        rows: list[dict[str, Any]] = []
        for row_number, raw_row in enumerate(raw_rows[1:], start=2):
            values = _normalize_values(raw_row, max_non_empty_col)
            if not any(values):
                continue
            rows.append(
                {
                    "rowNumber": row_number,
                    "values": values,
                }
            )

        return {
            "filePath": str(target),
            "exists": True,
            "sheetName": worksheet.title,
            "headers": headers,
            "rows": rows,
            "summary": {
                "columnCount": len(headers),
                "rowCount": len(rows),
            },
        }
    finally:
        workbook.close()


def save_factors_workbook(file_path: str | Path, headers: list[Any], rows: list[dict[str, Any] | list[Any]]) -> dict[str, Any]:
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    row_values: list[list[str]] = []
    max_row_width = 0
    for raw_row in rows or []:
        if isinstance(raw_row, dict):
            values = raw_row.get("values") or []
        elif isinstance(raw_row, list):
            values = raw_row
        else:
            values = []
        normalized = [_text(value) for value in list(values)]
        if any(normalized):
            row_values.append(normalized)
            max_row_width = max(max_row_width, len(normalized))

    column_count = max(1, len(headers or []), max_row_width)
    normalized_headers = _normalize_values(list(headers or []), column_count)
    normalized_rows = [_normalize_values(values, column_count) for values in row_values]

    workbook = openpyxl.load_workbook(target) if target.exists() else openpyxl.Workbook()
    try:
        worksheet = workbook.active
        existing_max_row = max(worksheet.max_row or 1, len(normalized_rows) + 1)
        existing_max_col = max(worksheet.max_column or 1, column_count)

        for row_number in range(1, existing_max_row + 1):
            for col_number in range(1, existing_max_col + 1):
                next_value: str | None = None
                if row_number == 1 and col_number <= column_count:
                    next_value = normalized_headers[col_number - 1] or None
                elif row_number >= 2:
                    data_index = row_number - 2
                    if data_index < len(normalized_rows) and col_number <= column_count:
                        next_value = normalized_rows[data_index][col_number - 1] or None
                worksheet.cell(row=row_number, column=col_number).value = next_value

        workbook.save(target)
    finally:
        workbook.close()

    return load_factors_workbook(target)
