from pathlib import Path
import io
from zipfile import ZipFile

import httpx
import openpyxl
import pytest

from pyserver.app import main
from pyserver.app.factor_prompt_artifacts import build_preview_prompt
from pyserver.app.main import app


async def login(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    response.raise_for_status()
    return response.json()["token"]


def _bootstrap_env(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))
    return repo_root, data_dir


def write_excel(path: Path, rows: list[list[object]]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


@pytest.mark.asyncio
async def test_generate_verify_builds_prompt_from_artifact_file(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)
    material_dir = tmp_path / "verify-material"
    material_dir.mkdir()
    artifact_path = tmp_path / "营业证照--要素提示词.json"
    artifact_path.write_text(
        """
        {
          "version": "1",
          "carriername": "营业证照",
          "template": {"prompt_template": "HEAD\\n$(factors)\\nTAIL"},
          "factors": [
            {
              "index": 1,
              "factorname": "统一社会信用代码",
              "factortype": "1",
              "factoruse": "企业识别",
              "factor_prompt": "识别18位字母数字组合",
              "source": "ai_generated"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    captured = {}

    def fake_run_verify_extraction(material_dir_arg, prompt_text, model, api_key, base_url="", extra_params=None, llm_logs=None):
        captured["material_dir"] = material_dir_arg
        captured["prompt_text"] = prompt_text
        captured["model"] = model
        return {
            "success": True,
            "image_file": "sample.jpg",
            "extraction_output": '{"msginfo":[]}',
            "error": "",
        }

    monkeypatch.setattr(main, "run_verify_extraction", fake_run_verify_extraction)

    expected_prompt = build_preview_prompt(
        "HEAD\n$(factors)\nTAIL",
        [
            {
                "factorname": "统一社会信用代码",
                "factor_prompt": "识别18位字母数字组合",
            }
        ],
    )

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            response = await client.post(
                "/api/generate/verify",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "materialDir": str(material_dir),
                    "promptText": "should be ignored",
                    "artifactFile": str(artifact_path),
                },
            )

    assert response.status_code == 200
    assert response.json()["data"]["success"] is True
    assert captured["material_dir"] == material_dir
    assert captured["prompt_text"] == expected_prompt
    assert captured["prompt_text"] != "should be ignored"


@pytest.mark.asyncio
async def test_generate_verify_builds_prompt_from_inline_artifact(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)
    material_dir = tmp_path / "verify-inline"
    material_dir.mkdir()

    captured = {}

    def fake_run_verify_extraction(material_dir_arg, prompt_text, model, api_key, base_url="", extra_params=None, llm_logs=None):
        captured["material_dir"] = material_dir_arg
        captured["prompt_text"] = prompt_text
        return {
            "success": True,
            "image_file": "sample.jpg",
            "extraction_output": '{"msginfo":[]}',
            "error": "",
        }

    monkeypatch.setattr(main, "run_verify_extraction", fake_run_verify_extraction)

    artifact = {
        "version": "1",
        "carriername": "营业证照",
        "template": {"prompt_template": "HEAD\n$(factors)\nTAIL"},
        "factors": [
            {
                "index": 1,
                "factorname": "企业名称",
                "factortype": "1",
                "factoruse": "企业全称",
                "factor_prompt": "识别完整企业名称",
                "source": "manual_edit",
            }
        ],
    }

    expected_prompt = build_preview_prompt(
        artifact["template"]["prompt_template"],
        artifact["factors"],
    )

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            response = await client.post(
                "/api/generate/verify",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "materialDir": str(material_dir),
                    "promptText": "fallback text",
                    "artifact": artifact,
                },
            )

    assert response.status_code == 200
    assert response.json()["data"]["success"] is True
    assert captured["material_dir"] == material_dir
    assert captured["prompt_text"] == expected_prompt
    assert captured["prompt_text"] != "fallback text"


@pytest.mark.asyncio
async def test_save_artifact_persists_normalized_json_and_preview(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)
    artifact_path = tmp_path / "营业证照--要素提示词.json"
    preview_path = tmp_path / "营业证照--要素提取完整提示词.txt"

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            response = await client.post(
                "/api/generate/save-artifact",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "filePath": str(artifact_path),
                    "previewFilePath": str(preview_path),
                    "artifact": {
                        "carriername": "营业证照",
                        "template": {"prompt_template": "HEAD\n$(factors)\nTAIL"},
                        "factors": [
                            {
                                "name": "统一社会信用代码",
                                "factoruse": "企业识别",
                                "rule": "识别18位字母数字组合",
                                "format": "保持原样",
                            }
                        ],
                    },
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    saved_artifact = payload["data"]["artifact"]
    assert saved_artifact["factors"][0]["factorname"] == "统一社会信用代码"
    assert saved_artifact["factors"][0]["factor_prompt"] == "识别18位字母数字组合，保持原样"
    assert saved_artifact["factors"][0]["source"] == "manual"

    saved_json = artifact_path.read_text(encoding="utf-8")
    preview_text = preview_path.read_text(encoding="utf-8")
    assert "统一社会信用代码" in saved_json
    assert "识别18位字母数字组合，保持原样" in saved_json
    assert "HEAD" in preview_text
    assert "## 1.统一社会信用代码" in preview_text
    assert "TAIL" in preview_text


@pytest.mark.asyncio
async def test_generate_download_result_bundles_generated_artifacts(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)

            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "generate-download"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])
            material_dir = work_dir / "营业证照"
            material_dir.mkdir(parents=True, exist_ok=True)
            write_excel(
                work_dir / "factors.xlsx",
                [
                    ["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"],
                    ["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#不能为空"],
                ],
            )
            (material_dir / "营业证照--要素提取完整提示词.txt").write_text("prompt", encoding="utf-8")
            (material_dir / "营业证照--要素提示词.json").write_text('{"ok":true}', encoding="utf-8")
            (material_dir / "营业证照--要素信息录入.json").write_text('{"factors":[]}', encoding="utf-8")

            response = await client.get(
                "/api/generate/download-result",
                headers={"Authorization": f"Bearer {token}"},
                params={"workDir": str(work_dir)},
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")

    with ZipFile(io.BytesIO(response.content)) as zf:
        names = set(zf.namelist())

    assert "营业证照/营业证照--要素提取完整提示词.txt" in names
    assert "营业证照/营业证照--要素提示词.json" in names
    assert "营业证照/营业证照--要素信息录入.json" in names
    assert "factors.xlsx" in names


@pytest.mark.asyncio
async def test_factors_workbook_routes_support_online_repair_and_revalidation(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)

            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "factors-repair"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])
            material_dir = work_dir / "营业证照"
            material_dir.mkdir(parents=True, exist_ok=True)
            (material_dir / "sample.jpg").write_bytes(b"img")
            write_excel(
                work_dir / "factors.xlsx",
                [
                    ["材料名称", "要素字段名称", "要素提取说明"],
                    ["营业证照", "统一社会信用代码", "企业唯一识别码"],
                ],
            )

            validation_response = await client.post(
                "/api/generate/validate-factors",
                headers={"Authorization": f"Bearer {token}"},
                json={"workDir": str(work_dir), "materials": ["营业证照"]},
            )
            validation_payload = validation_response.json()["data"]
            assert validation_payload["ok"] is False
            assert any(item.get("column") == "审查要点名称" for item in validation_payload.get("diagnostics", []))
            assert any(item.get("column") == "审查要点规则说明" for item in validation_payload.get("diagnostics", []))

            workbook_response = await client.get(
                "/api/workspaces/factors-workbook",
                headers={"Authorization": f"Bearer {token}"},
                params={"workDir": str(work_dir)},
            )
            workbook_payload = workbook_response.json()["data"]
            assert workbook_payload["headers"] == ["材料名称", "要素字段名称", "要素提取说明"]
            assert workbook_payload["rows"][0]["values"] == ["营业证照", "统一社会信用代码", "企业唯一识别码"]

            save_response = await client.put(
                "/api/workspaces/factors-workbook",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "workDir": str(work_dir),
                    "headers": [
                        "材料名称",
                        "要素字段名称",
                        "要素提取说明",
                        "审查要点名称",
                        "审查要点规则说明",
                    ],
                    "rows": [
                        {
                            "values": [
                                "营业证照",
                                "统一社会信用代码",
                                "企业唯一识别码",
                                "统一社会信用代码校验",
                                "#营业证照-统一社会信用代码#不能为空",
                            ]
                        }
                    ],
                },
            )

            assert save_response.status_code == 200
            save_payload = save_response.json()["data"]
            assert save_payload["validation"]["ok"] is True
            assert save_payload["validation"]["errors"] == []
            assert save_payload["workbook"]["headers"] == [
                "材料名称",
                "要素字段名称",
                "要素提取说明",
                "审查要点名称",
                "审查要点规则说明",
            ]
            assert save_payload["workbook"]["rows"][0]["values"][3:] == [
                "统一社会信用代码校验",
                "#营业证照-统一社会信用代码#不能为空",
            ]
