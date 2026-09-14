import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import AuthSession, AuthUser
from app.security import generate_password, hash_password


def _purge_test_user(username: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(AuthUser).filter(AuthUser.username == username).first()
        if user:
            db.query(AuthSession).filter(AuthSession.user_id == user.id).delete(
                synchronize_session=False
            )
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _login_client(username: str) -> tuple[TestClient, str]:
    password = generate_password()
    _purge_test_user(username)
    db = SessionLocal()
    try:
        db.add(AuthUser(username=username, password_hash=hash_password(password)))
        db.commit()
    finally:
        db.close()
    client = TestClient(app)
    ok = client.post("/api/auth/login", json={"username": username, "password": password})
    assert ok.status_code == 200
    return client, password


def test_database_download_and_upload_require_session():
    client = TestClient(app)
    assert client.get("/api/data/database").status_code == 401
    assert client.post("/api/data/database").status_code == 401


def test_database_download_returns_sqlite():
    username = "test-data-download"
    try:
        client, _password = _login_client(username)
        res = client.get("/api/data/database")
        assert res.status_code == 200
        assert res.content[:16] == b"SQLite format 3\x00"
        assert "ledger-" in res.headers.get("content-disposition", "")
    finally:
        _purge_test_user(username)


def test_database_upload_requires_confirm(tmp_path: Path):
    username = "test-data-noconfirm"
    source = tmp_path / "source.db"
    conn = sqlite3.connect(source)
    conn.execute(
        "CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, account_type TEXT)"
    )
    conn.execute("INSERT INTO accounts VALUES (1, 'Nope', 'bank')")
    conn.commit()
    conn.close()
    try:
        client, _password = _login_client(username)
        with source.open("rb") as fh:
            res = client.post(
                "/api/data/database",
                files={"file": ("ledger.db", fh, "application/octet-stream")},
            )
        assert res.status_code == 400
        assert "Confirm" in res.json()["detail"]
    finally:
        _purge_test_user(username)


def test_database_upload_rejects_garbage(tmp_path: Path):
    username = "test-data-garbage"
    junk = tmp_path / "junk.txt"
    junk.write_text("hello")
    try:
        client, _password = _login_client(username)
        with junk.open("rb") as fh:
            res = client.post(
                "/api/data/database?confirm=true",
                files={"file": ("junk.txt", fh, "text/plain")},
            )
        assert res.status_code == 400
    finally:
        _purge_test_user(username)
