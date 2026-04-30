from pathlib import Path

import httpx
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
