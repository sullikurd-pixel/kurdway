"""Local SQLite schema; no real customer data until security review."""
import sqlite3
from pathlib import Path
import os

def initialize():
    folder = Path.home() / ".kurdway"
    folder.mkdir(mode=0o700, exist_ok=True)
    if folder.is_symlink():
        raise RuntimeError("Unsafe database directory")
    os.chmod(folder, 0o700)
    path = folder / "development.sqlite3"
    if path.is_symlink():
        raise RuntimeError("Unsafe database path")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    os.chmod(path, 0o600)
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
            plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free','premium')),
            email_verified_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("SELECT id, email, role, plan FROM users LIMIT 0")
    return True
