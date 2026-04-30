from pathlib import Path
from zipfile import ZipFile
import io

import httpx
import pytest

from pyserver.app import main
from pyserver.app.main import app, validate_classify_workspace


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


def test_validate_classify_workspace_accepts_missing_classified_dir(tmp_path, monkeypatch):
    repo_root, _ = _bootstrap_env(tmp_path, monkeypatch)
    work_dir = repo_root / "workspace"
    pending_dir = work_dir / "待分类材料"
    pending_dir.mkdir(parents=True, exist_ok=True)
    (pending_dir / "a.jpg").write_bytes(b"fake")
    (work_dir / "factors.csv").write_text("事项名称,材料名称,字段\n事项A,材料A,字段A\n", encoding="utf-8")

    monkeypatch.setattr(main, "read_factors_script", lambda _paths, _dir: [{"material": "材料A"}])
    paths = type("Paths", (), {"repo_root": repo_root, "skills_dir": repo_root / "skills"})()
    result = validate_classify_workspace(paths, str(work_dir))

    assert result["ok"] is True
    assert any("自动创建" in msg for msg in result["warnings"])


@pytest.mark.asyncio
async def test_classify_download_result_includes_prompts_and_report(tmp_path, monkeypatch):
    repo_root, _ = _bootstrap_env(tmp_path, monkeypatch)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await login(client)

            workspace_resp = await client.post(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
                data={"name": "zip-test"},
            )
            workspace = workspace_resp.json()
            work_dir = Path(workspace["rootPath"])

            classified = work_dir / "已分类材料" / "材料A"
            classified.mkdir(parents=True, exist_ok=True)
            (classified / "1.jpg").write_bytes(b"img")
            (work_dir / "最新分类信息提取提示词.txt").write_text("extract", encoding="utf-8")
            (work_dir / "最新分类附件归集提示词.txt").write_text("aggregate", encoding="utf-8")
            (work_dir / "classification_report.json").write_text('{"ok":true}', encoding="utf-8")

            resp = await client.get(
                "/api/classify/download-result",
                headers={"Authorization": f"Bearer {token}"},
                params={"workDir": str(work_dir)},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("application/zip")

            with ZipFile(io.BytesIO(resp.content)) as zf:
                names = set(zf.namelist())

            assert "已分类材料/材料A/1.jpg" in names
            assert "最新分类信息提取提示词.txt" in names
            assert "最新分类附件归集提示词.txt" in names
            assert "classification_report.json" in names
