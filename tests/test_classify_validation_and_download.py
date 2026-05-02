from pathlib import Path
from zipfile import ZipFile
import io

import httpx
import pytest

from pyserver.app import main
from pyserver.app.main import app, validate_workspace_bundle


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


def test_validate_classify_workspace_uses_shared_workspace_rules(tmp_path, monkeypatch):
    repo_root, _ = _bootstrap_env(tmp_path, monkeypatch)
    work_dir = repo_root / "workspace"
    material_dir = work_dir / "材料A"
    material_dir.mkdir(parents=True, exist_ok=True)
    (material_dir / "a.jpg").write_bytes(b"fake")

    wb_path = work_dir / "factors.xlsx"
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"])
    ws.append(["材料A", "字段A", "字段说明", "字段A校验", "#材料A-字段A#不能为空"])
    wb.save(wb_path)
    wb.close()

    paths = type("Paths", (), {"repo_root": repo_root, "skills_dir": repo_root / "skills"})()
    result = validate_workspace_bundle(paths, str(work_dir))

    assert result["ok"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_classify_download_result_includes_prompt_artifact_and_report(tmp_path, monkeypatch):
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

            material_dir = work_dir / "材料A"
            material_dir.mkdir(parents=True, exist_ok=True)
            (material_dir / "1.jpg").write_bytes(b"img")
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.append(["材料名称", "要素字段名称", "要素提取说明", "审查要点名称", "审查要点规则说明"])
            ws.append(["材料A", "字段A", "字段说明", "字段A校验", "#材料A-字段A#不能为空"])
            wb.save(work_dir / "factors.xlsx")
            wb.close()
            (work_dir / "材料分类提示词.json").write_text('{"version":"1"}', encoding="utf-8")
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

            assert "材料分类提示词.json" in names
            assert "最新分类信息提取提示词.txt" in names
            assert "最新分类附件归集提示词.txt" in names
            assert "classification_report.json" in names
            assert "factors.xlsx" in names
