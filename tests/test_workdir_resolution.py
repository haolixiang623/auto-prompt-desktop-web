from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi import HTTPException

from pyserver.app.core.paths import AppPaths
from pyserver.app.main import _resolve_user_file_path, _resolve_user_work_dir, build_zip_archive


@pytest.fixture
def app_paths(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))
    return AppPaths()


def test_resolve_user_work_dir_keeps_absolute_workspace_path_for_current_user(app_paths):
    user_id = "user-123"
    workspace = app_paths.user_workspace_root / user_id / "workspace-1"
    workspace.mkdir(parents=True, exist_ok=True)

    resolved = _resolve_user_work_dir(app_paths, str(workspace), user_id)

    assert resolved == str(workspace)


def test_resolve_user_work_dir_rejects_other_users_absolute_workspace_path(app_paths):
    current_user_id = "user-123"
    other_workspace = app_paths.user_workspace_root / "user-456" / "workspace-1"
    other_workspace.mkdir(parents=True, exist_ok=True)

    with pytest.raises(HTTPException) as exc_info:
        _resolve_user_work_dir(app_paths, str(other_workspace), current_user_id)

    assert exc_info.value.status_code == 403


def test_resolve_user_work_dir_maps_relative_workspace_path_into_current_user_root(app_paths):
    user_id = "user-123"
    work_dir = "workspace-1"

    resolved = _resolve_user_work_dir(app_paths, work_dir, user_id)

    assert resolved == str(app_paths.user_workspace_root / user_id / work_dir)


def test_resolve_user_file_path_allows_current_user_workspace_file(app_paths):
    user_id = "user-123"
    target = app_paths.user_workspace_root / user_id / "workspace-1" / "result.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"ok": true}', encoding="utf-8")

    resolved = _resolve_user_file_path(app_paths, str(target), user_id)

    assert resolved == target.resolve()


def test_resolve_user_file_path_rejects_other_user_workspace_file(app_paths):
    current_user_id = "user-123"
    target = app_paths.user_workspace_root / "user-456" / "workspace-1" / "result.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"ok": true}', encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        _resolve_user_file_path(app_paths, str(target), current_user_id)

    assert exc_info.value.status_code == 403


def test_build_zip_archive_contains_all_requested_json_files(tmp_path):
    first = tmp_path / "身份证--要素信息录入.json"
    second = tmp_path / "银行卡--要素信息录入.json"
    first.write_text('{"material":"身份证"}', encoding="utf-8")
    second.write_text('{"material":"银行卡"}', encoding="utf-8")

    archive = build_zip_archive([first, second])

    with ZipFile(BytesIO(archive)) as zip_file:
        assert sorted(zip_file.namelist()) == sorted([first.name, second.name])
        assert zip_file.read(first.name).decode("utf-8") == '{"material":"身份证"}'
        assert zip_file.read(second.name).decode("utf-8") == '{"material":"银行卡"}'
