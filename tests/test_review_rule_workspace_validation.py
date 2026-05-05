from pathlib import Path

import openpyxl

from pyserver.app import main


def write_excel(path: Path, rows: list[list[object]]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def make_paths(tmp_path):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return type(
        "Paths",
        (),
        {
            "repo_root": repo_root,
            "data_dir": data_dir,
            "user_workspace_root": data_dir / "workspaces",
        },
    )()


def test_validate_review_rule_workspace_rejects_factor_prompt_template(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-a"
    work_dir.mkdir(parents=True)
    material_dir = work_dir / "营业证照"
    material_dir.mkdir()
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素名称", "要素提取说明", "提取规则说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码", "18位字母数字组合"],
        ],
    )

    result = main.validate_review_rule_workspace(paths, str(work_dir))

    assert result["ok"] is False
    assert any("审查要点名称" in message for message in result["errors"])
    assert any("审查要点规则说明" in message for message in result["errors"])
    assert result["meta"]["headers"][:4] == ["材料名称", "要素名称", "要素提取说明", "提取规则说明"]


def test_validate_review_rule_workspace_accepts_review_rule_template(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-b"
    work_dir.mkdir(parents=True)
    material_dir = work_dir / "营业证照"
    material_dir.mkdir()
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#需为18位字母数字组合"],
            [None, "企业名称", "企业名称", "企业名称校验", "#营业证照-企业名称#不能为空"],
        ],
    )

    result = main.validate_review_rule_workspace(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["meta"]["keypoint_count"] == 2
    assert result["meta"]["material_count"] == 1


def test_validate_review_rule_workspace_returns_structured_diagnostics_for_invalid_placeholder(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-c"
    work_dir.mkdir(parents=True)
    material_dir = work_dir / "营业证照"
    material_dir.mkdir()
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "需要晚于#当前月份#的月份"],
        ],
    )

    result = main.validate_review_rule_workspace(paths, str(work_dir))

    assert result["ok"] is False
    assert any("当前月份" in message for message in result["errors"])
    assert any(
        item.get("row") == 2
        and item.get("column") == "审查要点规则说明"
        and item.get("token") == "当前月份"
        for item in result.get("diagnostics", [])
    )


def test_validate_review_rule_workspace_accepts_current_material_shorthand_factor_ref(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-short-factor"
    work_dir.mkdir(parents=True)
    material_dir = work_dir / "机动车登记证书"
    material_dir.mkdir()
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["机动车登记证书", "车牌照号", "车辆号牌", "车牌照号校验", "#车牌照号#不能为空"],
        ],
    )

    result = main.validate_review_rule_workspace(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []
