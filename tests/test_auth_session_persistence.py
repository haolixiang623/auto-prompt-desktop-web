from datetime import datetime, timedelta
from types import SimpleNamespace
import sqlite3

import httpx
import pytest

from pyserver.app.main import AuthStore, app


def test_auth_store_persists_sessions_without_modifying_existing_users(tmp_path):
    db_path = tmp_path / "auth.db"
    store = AuthStore(db_path)
    store.create_user(SimpleNamespace(name="Alice", username="alice", password="secret123"))
    user = store.authenticate("alice", "secret123")

    session = store.create_session(user, remember_me=True)

    reloaded = AuthStore(db_path)
    restored_user = reloaded.get_user_from_token(session["token"])

    assert restored_user is not None
    assert restored_user.username == "alice"

    with sqlite3.connect(str(db_path)) as conn:
        usernames = [
            row[0]
            for row in conn.execute(
                "SELECT username FROM users WHERE username IN ('admin', 'alice') ORDER BY username"
            ).fetchall()
        ]

    assert usernames == ["admin", "alice"]


def test_auth_store_rejects_and_cleans_expired_sessions(tmp_path):
    db_path = tmp_path / "auth.db"
    store = AuthStore(db_path)
    user = store.authenticate("admin", "admin123456")
    expired_at = (datetime.utcnow() - timedelta(days=1)).isoformat()

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            ("expired-token", user.id, expired_at, expired_at),
        )
        conn.commit()

    assert store.get_user_from_token("expired-token") is None

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT token FROM sessions WHERE token = ?", ("expired-token",)).fetchone()

    assert row is None


@pytest.mark.asyncio
async def test_login_route_returns_session_expiry_for_remember_me(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = repo_root / ".runtime-data"
    repo_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AUTO_PROMPT_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("AUTO_PROMPT_DATA_DIR", str(data_dir))

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123456", "rememberMe": True},
            )

            response.raise_for_status()
            payload = response.json()

    assert payload["token"]
    assert payload["user"]["username"] == "admin"
    assert payload["expiresAt"]
