"""Generate a one-user password, hash it, and store only the hash."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, ensure_schema
from app.models import AuthSession, AuthUser
from app.security import generate_password, hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or rotate the single Ledger login.")
    parser.add_argument("--username", default="ledger", help="Login name (default: ledger)")
    args = parser.parse_args()
    username = args.username.strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    ensure_schema()
    password = generate_password()
    password_hash = hash_password(password)

    db = SessionLocal()
    try:
        db.query(AuthSession).delete(synchronize_session=False)
        db.query(AuthUser).delete(synchronize_session=False)
        db.add(AuthUser(username=username, password_hash=password_hash))
        db.commit()
    finally:
        db.close()

    print()
    print("Ledger login created. The password is shown once and is not stored in plaintext.")
    print()
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print()
    print("Save it in a password manager. On the VPS set LEDGER_SECURE_COOKIES=1 behind HTTPS.")
    print()


if __name__ == "__main__":
    main()
