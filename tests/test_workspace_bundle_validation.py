import json
from pathlib import Path

import httpx
import openpyxl
import pytest

from pyserver.app import main
from pyserver.app.main import app


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


async def login(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    response.raise_for_status()
    return response.json()["token"]


def test_validate_workspace_bundle_accepts_combined_workspace(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-a"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#需为18位字母数字组合"],
            [None, "企业名称", "企业名称", "企业名称校验", "#营业证照-企业名称#不能为空"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["meta"]["material_count"] == 1
    assert result["meta"]["factor_count"] == 2
    assert result["meta"]["keypoint_count"] == 2
    assert result["meta"]["sample_file_count"] == 1


def test_validate_workspace_bundle_rejects_missing_review_columns_even_for_generate(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-b"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is False
    assert any("审查要点名称" in message for message in result["errors"])
    assert any("审查要点规则说明" in message for message in result["errors"])


def test_validate_workspace_bundle_rejects_missing_factor_reference_in_review_rule(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-c"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#需为18位字母数字组合"],
            [None, None, None, "企业名称校验", "#营业证照-企业名称#不能为空"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is False
    assert any("营业证照-企业名称" in message for message in result["errors"])


def test_validate_workspace_bundle_allows_review_rule_without_any_placeholder_refs(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-d"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "有效期月份", "月份", "月份校验", "月份格式应为两位数字且不得为空"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []


def test_validate_workspace_bundle_accepts_default_builtin_variable_refs(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-e"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "有效期月份", "月份", "月份校验", "需要晚于#当前日期#的月份"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []


def test_validate_workspace_bundle_rejects_unknown_placeholder_token(tmp_path):
    paths = make_paths(tmp_path)
    work_dir = paths.user_workspace_root / "user-1" / "workspace-f"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "有效期月份", "月份", "月份校验", "需要晚于#当前月份#的月份"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is False
    assert any("当前月份" in message for message in result["errors"])


def test_validate_workspace_bundle_accepts_custom_builtin_variable_from_settings(tmp_path):
    paths = make_paths(tmp_path)
    paths.settings_path = paths.data_dir / "settings.json"
    paths.settings_path.write_text(
        json.dumps(
            {
                "review_rule_builtin_variables": [
                    {
                        "token": "当前月份",
                        "name": "当前月份",
                        "placeholder": "$系统变量:当前月份$",
                        "dataType": "string",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    work_dir = paths.user_workspace_root / "user-1" / "workspace-g"
    material_dir = work_dir / "营业证照"
    material_dir.mkdir(parents=True)
    (material_dir / "sample.jpg").write_bytes(b"fake")
    write_excel(
        work_dir / "factors.xlsx",
        [
            ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
            ["营业证照", "有效期月份", "月份", "月份校验", "需要晚于#当前月份#的月份"],
        ],
    )

    result = main.validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_all_three_validation_routes_share_the_same_workspace_rules(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "shared-validation"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])
            material_dir = work_dir / "营业证照"
            material_dir.mkdir(parents=True, exist_ok=True)
            (material_dir / "sample.jpg").write_bytes(b"fake")
            write_excel(
                work_dir / "factors.xlsx",
                [
                    ["材料名称", "要素字段名称", "要素提取说明"],
                    ["营业证照", "统一社会信用代码", "企业唯一识别码"],
                ],
            )

            classify_resp = await client.post(
                "/api/classify/validate-workdir",
                headers={"Authorization": f"Bearer {token}"},
                json={"workDir": str(work_dir)},
            )
            generate_resp = await client.post(
                "/api/generate/validate-factors",
                headers={"Authorization": f"Bearer {token}"},
                json={"workDir": str(work_dir), "materials": []},
            )
            review_resp = await client.post(
                "/api/review-rule/validate-workspace",
                headers={"Authorization": f"Bearer {token}"},
                json={"workDir": str(work_dir)},
            )

    classify_data = classify_resp.json()["data"]
    generate_data = generate_resp.json()["data"]
    review_data = review_resp.json()["data"]

    assert classify_data["ok"] is False
    assert generate_data["ok"] is False
    assert review_data["ok"] is False
    assert classify_data["errors"] == generate_data["errors"] == review_data["errors"]
