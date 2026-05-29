#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def auth_db_path() -> Path:
    configured = os.getenv("FF_OPERATOR_AUTH_DATABASE_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    return repo_root() / "instance" / "ff_operator_auth.sqlite3"


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ff_operator_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'organizer',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        )
        """
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update a FutureFunded operator user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--role", default="organizer")
    parser.add_argument("--password", default="")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")

    if not args.password:
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise SystemExit("Passwords do not match.")

    if len(password) < 10:
        raise SystemExit("Use a password with at least 10 characters.")

    db_path = auth_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        conn.execute(
            """
            INSERT INTO ff_operator_users (email, name, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                password_hash = excluded.password_hash,
                role = excluded.role,
                is_active = 1
            """,
            (
                args.email.strip().lower(),
                args.name.strip(),
                generate_password_hash(password),
                args.role.strip() or "organizer",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Operator user ready: {args.email.strip().lower()}")
    print(f"Auth DB: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
