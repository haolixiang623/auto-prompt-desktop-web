from pathlib import Path

import httpx
import pytest

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


@pytest.mark.asyncio
async def test_generate_workspace_is_listed_immediately_after_marking_activity(tmp_path, monkeypatch):
    _bootstrap_env(tmp_path, monkeypatch)

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)
            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "generate-listing"},
            )
            workspace_resp.raise_for_status()
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])

            mark_resp = await client.put(
                "/api/workspaces/activity",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "workDir": str(work_dir),
                    "module": "generate",
                    "status": "generating",
                },
            )
            mark_resp.raise_for_status()

            list_resp = await client.get(
                "/api/workspaces/list",
                headers={"Authorization": f"Bearer {token}"},
                params={"module": "generate"},
            )
            list_resp.raise_for_status()
            workspaces = list_resp.json()

    matched = next((item for item in workspaces if item["rootPath"] == str(work_dir)), None)

    assert matched is not None
    assert matched["module"] == "generate"
    assert matched["genStatus"] == "generating"
