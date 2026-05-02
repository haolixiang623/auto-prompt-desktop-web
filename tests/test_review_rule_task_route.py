import asyncio
import io
import time
from pathlib import Path
from zipfile import ZipFile

import httpx
import openpyxl
import pytest

from pyserver.app import main
from pyserver.app.main import app


async def login(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    response.raise_for_status()
    return response.json()["token"]


@pytest.mark.asyncio
async def test_review_rule_task_route_returns_task_instead_of_internal_server_error(tmp_path, monkeypatch):
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
            response = await client.post(
                "/api/tasks/review-rule",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "workDir": "",
                    "useLlm": False,
                },
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["kind"] == "review_rule"
            assert payload["status"] in {"running", "succeeded", "failed"}


@pytest.mark.asyncio
async def test_settings_test_model_route_uses_supplied_model_payload(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))

    captured = {}

    def fake_test_model_connection(model, fallback_api_key="", timeout=30):
        captured["model"] = model
        captured["fallback_api_key"] = fallback_api_key
        captured["timeout"] = timeout
        return {"ok": True, "model": model.get("model"), "elapsed_s": 0.1, "preview": "OK"}

    monkeypatch.setattr(main, "test_model_connection", fake_test_model_connection)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            response = await client.post(
                "/api/settings/test-model",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "fallbackApiKey": "fallback-key",
                    "timeout": 45,
                    "model": {
                        "id": "fast",
                        "name": "Fast",
                        "model": "fast-model",
                        "base_url": "https://fast.example/v1",
                        "api_key": "",
                        "params": [{"key": "enable_thinking", "value": False}],
                    },
                },
            )

            assert response.status_code == 200
            assert response.json()["ok"] is True
            assert captured["fallback_api_key"] == "fallback-key"
            assert captured["timeout"] == 45
            assert captured["model"]["model"] == "fast-model"


def test_run_review_rule_enables_llm_and_uses_payload_overrides(tmp_path, monkeypatch):
    captured = {}

    def fake_run_lines(cmd, env, cwd, log_cb=None):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["cwd"] = cwd
        return ["RESULTS_JSON:[]"]

    monkeypatch.setattr(main, "run_lines", fake_run_lines)

    paths = type("Paths", (), {"skills_dir": tmp_path})()

    result = main.run_review_rule(
        paths,
        {"api_key": "stored-key", "model_name": "stored-model"},
        "/tmp/workspace",
        True,
        api_key="payload-key",
        base_url="https://example.invalid/v1",
        model="payload-model",
    )

    assert result == []
    assert "--use-llm" in captured["cmd"]
    assert captured["cmd"][-8:] == [
        "--api-key",
        "payload-key",
        "--base-url",
        "https://example.invalid/v1",
        "--model",
        "payload-model",
        "--timeout",
        "120",
    ]


@pytest.mark.asyncio
async def test_cancel_task_route_marks_generate_task_as_cancelled(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))

    def fake_run_generate_prompt(
        paths,
        settings,
        work_dir,
        material_name,
        model_cfg_id=None,
        use_case_library=True,
        rule_profile_id=None,
        task_store=None,
        task_id=None,
    ):
        assert task_store is not None
        assert task_id is not None
        while not task_store.is_cancel_requested(task_id):
            time.sleep(0.01)
        raise main.TaskCancelledError("已停止生成")

    monkeypatch.setattr(main, "run_generate_prompt", fake_run_generate_prompt)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "generate-cancel"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])
            material_dir = work_dir / "营业证照"
            material_dir.mkdir(parents=True, exist_ok=True)
            (material_dir / "sample.jpg").write_bytes(b"fake")

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"])
            ws.append(["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#不能为空"])
            wb.save(work_dir / "factors.xlsx")
            wb.close()

            start_response = await client.post(
                "/api/tasks/generate",
                headers={"Authorization": f"Bearer {token}"},
                json={"workDir": str(work_dir), "materialName": "营业证照"},
            )

            assert start_response.status_code == 200
            task_id = start_response.json()["id"]

            cancel_response = await client.post(
                f"/api/task-runs/{task_id}/cancel",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert cancel_response.status_code == 200

            final_payload = None
            for _ in range(50):
                status_response = await client.get(
                    f"/api/task-runs/{task_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                status_response.raise_for_status()
                final_payload = status_response.json()
                if final_payload["status"] == "cancelled":
                    break
                await asyncio.sleep(0.02)

            assert final_payload is not None
            assert final_payload["status"] == "cancelled"
            assert "已停止生成" in (final_payload.get("error") or "")


@pytest.mark.asyncio
async def test_review_rule_download_result_bundles_generated_json(tmp_path, monkeypatch):
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
                data={"name": "review-download"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])
            material_dir = work_dir / "营业证照"
            material_dir.mkdir(parents=True, exist_ok=True)
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.append(["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"])
            ws.append(["营业证照", "统一社会信用代码", "企业唯一识别码", "统一社会信用代码校验", "#营业证照-统一社会信用代码#不能为空"])
            wb.save(work_dir / "factors.xlsx")
            wb.close()
            (material_dir / "营业证照--审查规则导入.json").write_text('{"keypoints":[]}', encoding="utf-8")

            response = await client.get(
                "/api/review-rule/download-result",
                headers={"Authorization": f"Bearer {token}"},
                params={"workDir": str(work_dir)},
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")

    with ZipFile(io.BytesIO(response.content)) as zf:
        names = set(zf.namelist())

    assert "营业证照/营业证照--审查规则导入.json" in names
    assert "factors.xlsx" in names
