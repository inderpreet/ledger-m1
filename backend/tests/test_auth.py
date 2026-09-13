from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import AuthSession, AuthUser
from app.security import generate_password, hash_password, verify_password


def test_password_hash_is_not_plaintext_and_verifies():
    password = generate_password()
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_generated_passwords_are_unique_and_long():
    first = generate_password()
    second = generate_password()
    assert first != second
    assert len(first) >= 32


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


def test_protected_routes_need_session_and_login_works():
    username = "test-auth-user"
    password = generate_password()
    _purge_test_user(username)
    db = SessionLocal()
    try:
        db.add(AuthUser(username=username, password_hash=hash_password(password)))
        db.commit()
    finally:
        db.close()

    try:
        client = TestClient(app)
        denied = client.get("/api/settings")
        assert denied.status_code == 401

        bad = client.post("/api/auth/login", json={"username": username, "password": "nope"})
        assert bad.status_code == 401

        ok = client.post("/api/auth/login", json={"username": username, "password": password})
        assert ok.status_code == 200
        assert ok.json()["username"] == username
        assert "ledger_session" in ok.cookies

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        settings = client.get("/api/settings")
        assert settings.status_code == 200

        client.post("/api/auth/logout")
        after = client.get("/api/settings")
        assert after.status_code == 401
    finally:
        _purge_test_user(username)
