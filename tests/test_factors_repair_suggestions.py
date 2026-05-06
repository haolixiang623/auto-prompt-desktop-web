from __future__ import annotations

import pytest


from pyserver.app.factors_repair_suggestions import generate_factors_repair_suggestions


def build_workbook_payload() -> dict:
    return {
        "headers": ["事项名称", "材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {
                "rowNumber": 2,
                "values": ["道路运输证申领", "营业证照", "统一社会信用代码", "", ""],
            },
            {
                "rowNumber": 3,
                "values": ["道路运输证申领", "营业证照", "企业名称", "", ""],
            },
            {
                "rowNumber": 4,
                "values": ["道路运输证申领", "营业证照", "", "统一社会信用代码校验", "#营业证照-统一社会信用代吗#不能为空"],
            },
        ],
        "mergedRanges": [],
    }


@pytest.mark.asyncio
async def test_generate_repair_suggestions_fuzzy_matches_missing_referenced_factor():
    payload = build_workbook_payload()
    diagnostics = [
        {
            "id": "diagnostic-1",
            "code": "missing_referenced_factor",
            "row": 4,
            "column": "审查要点规则说明",
            "materialName": "营业证照",
            "factorName": "统一社会信用代吗",
            "token": "营业证照-统一社会信用代吗",
            "message": "引用的要素不存在",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    assert result["stats"]["suggested"] == 1
    item = result["items"][0]
    assert item["diagnosticId"] == "diagnostic-1"
    assert item["requiresConfirmation"] is True
    assert item["status"] == "suggested"
    assert item["patches"] == [
        {
            "type": "cell_update",
            "rowNumber": 4,
            "columnIndex": 4,
            "before": "#营业证照-统一社会信用代吗#不能为空",
            "after": "#营业证照-统一社会信用代码#不能为空",
        }
    ]
    assert item["confidence"] >= 0.8


@pytest.mark.asyncio
async def test_generate_repair_suggestions_repairs_missing_referenced_material():
    payload = {
        "headers": ["事项名称", "材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {
                "rowNumber": 2,
                "values": ["道路运输证申领", "机动车登记证书(产权证)", "燃料种类", "", ""],
            },
            {
                "rowNumber": 3,
                "values": ["道路运输证申领", "道路运输证申领登记表", "", "燃油类型需一致", "需与#机动车登记证书（产权证）-燃料种类#一致"],
            },
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-material-1",
            "code": "missing_referenced_material",
            "row": 3,
            "column": "审查要点规则说明",
            "materialName": "机动车登记证书（产权证）",
            "message": "引用的材料不存在对应要素定义",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["patches"] == [
        {
            "type": "cell_update",
            "rowNumber": 3,
            "columnIndex": 4,
            "before": "需与#机动车登记证书（产权证）-燃料种类#一致",
            "after": "需与#机动车登记证书(产权证)-燃料种类#一致",
        }
    ]
    assert item["confidence"] >= 0.8


@pytest.mark.asyncio
async def test_generate_repair_suggestions_clones_factor_rows_for_missing_material_definitions():
    payload = {
        "headers": ["事项名称", "材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {
                "rowNumber": 2,
                "values": ["道路运输证申领", "营业证照", "统一社会信用代码", "", ""],
            },
            {
                "rowNumber": 3,
                "values": ["道路运输证申领", "营业证照", "企业名称", "", ""],
            },
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-material-factors-1",
            "code": "missing_factor_definition_for_material",
            "materialName": "营业执照",
            "message": "工作区材料目录存在附件，但 factors.xlsx 中没有对应要素定义。",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert [patch["type"] for patch in item["patches"]] == ["row_insert", "row_insert"]
    assert item["patches"][0]["rowValues"] == ["道路运输证申领", "营业执照", "统一社会信用代码", "", ""]
    assert item["patches"][1]["rowValues"] == ["道路运输证申领", "营业执照", "企业名称", "", ""]
    assert item["confidence"] >= 0.58


@pytest.mark.asyncio
async def test_generate_repair_suggestions_can_copy_workspace_material_files_for_missing_directory():
    payload = {
        "headers": ["事项名称", "材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {
                "rowNumber": 2,
                "values": ["道路运输证申领", "营业证照", "统一社会信用代码", "", ""],
            },
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-material-dir-1",
            "code": "missing_material_directory",
            "materialName": "营业证照",
            "message": "材料目录缺失。",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
        workspace_materials=[
            {
                "name": "营业执照",
                "image_count": 2,
                "path": "/tmp/workspace/营业执照",
            }
        ],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["patches"] == [
        {
            "type": "workspace_material_clone",
            "sourceMaterialName": "营业执照",
            "targetMaterialName": "营业证照",
            "sourceFileCount": 2,
        }
    ]
    assert item["confidence"] >= 0.58


@pytest.mark.asyncio
async def test_generate_repair_suggestions_inserts_missing_factor_when_no_match():
    payload = build_workbook_payload()
    diagnostics = [
        {
            "id": "diagnostic-2",
            "code": "missing_referenced_factor",
            "row": 4,
            "column": "审查要点规则说明",
            "materialName": "营业证照",
            "factorName": "注册资本",
            "token": "营业证照-注册资本",
            "message": "引用的要素不存在",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["patches"][0]["type"] == "row_insert"
    assert item["patches"][0]["afterRowNumber"] == 4
    assert item["patches"][0]["rowValues"] == [
        "道路运输证申领",
        "营业证照",
        "注册资本",
        "",
        "",
    ]


@pytest.mark.asyncio
async def test_generate_repair_suggestions_repairs_invalid_shorthand_placeholder():
    payload = {
        "headers": ["材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {"rowNumber": 2, "values": ["机动车行驶证", "号牌号码", "", ""]},
            {"rowNumber": 3, "values": ["机动车行驶证", "", "号牌校验", "#车牌号#应与系统一致"]},
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-3",
            "code": "invalid_placeholder",
            "row": 3,
            "column": "审查要点规则说明",
            "materialName": "机动车行驶证",
            "token": "车牌号",
            "message": "占位符无效",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["patches"] == [
        {
            "type": "cell_update",
            "rowNumber": 3,
            "columnIndex": 3,
            "before": "#车牌号#应与系统一致",
            "after": "#号牌号码#应与系统一致",
        }
    ]


@pytest.mark.asyncio
async def test_generate_repair_suggestions_uses_llm_for_empty_rule_description():
    payload = {
        "headers": ["材料名称", "要素字段名称", "审查要点名称", "审查要点规则说明"],
        "rows": [
            {"rowNumber": 2, "values": ["营业证照", "统一社会信用代码", "", ""]},
            {"rowNumber": 3, "values": ["营业证照", "", "统一社会信用代码校验", ""]},
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-4",
            "code": "empty_rule_description",
            "row": 3,
            "column": "审查要点规则说明",
            "materialName": "营业证照",
            "keypointName": "统一社会信用代码校验",
            "message": "规则说明为空",
        }
    ]

    async def fake_llm_suggester(context: dict) -> dict:
        assert context["materialName"] == "营业证照"
        assert context["keypointName"] == "统一社会信用代码校验"
        return {
            "content": "#统一社会信用代码#不能为空，且应为18位字母或数字组合",
            "reason": "结合同材料要素与审查要点名称生成候选规则说明。",
            "confidence": 0.67,
        }

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
        llm_rule_description_suggester=fake_llm_suggester,
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["usedLlm"] is True
    assert item["patches"] == [
        {
            "type": "cell_update",
            "rowNumber": 3,
            "columnIndex": 3,
            "before": "",
            "after": "#统一社会信用代码#不能为空，且应为18位字母或数字组合",
        }
    ]


@pytest.mark.asyncio
async def test_generate_repair_suggestions_marks_duplicate_rows_for_manual_delete():
    payload = {
        "headers": ["材料名称", "要素字段名称", "要素提取说明"],
        "rows": [
            {"rowNumber": 2, "values": ["营业证照", "统一社会信用代码", "企业唯一识别码"]},
            {"rowNumber": 3, "values": ["营业证照", "统一社会信用代码", "企业唯一识别码"]},
        ],
        "mergedRanges": [],
    }
    diagnostics = [
        {
            "id": "diagnostic-5",
            "code": "duplicate_factor",
            "materialName": "营业证照",
            "factorName": "统一社会信用代码",
            "rowNumbers": [2, 3],
            "message": "重复要素",
        }
    ]

    result = await generate_factors_repair_suggestions(
        headers=payload["headers"],
        rows=payload["rows"],
        merged_ranges=payload["mergedRanges"],
        diagnostics=diagnostics,
        builtin_variables=[],
    )

    item = result["items"][0]
    assert item["status"] == "suggested"
    assert item["patches"] == [
        {
            "type": "row_delete",
            "rowNumber": 3,
        }
    ]
