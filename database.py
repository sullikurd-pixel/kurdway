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
        columns = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        if "blocked" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN blocked INTEGER NOT NULL DEFAULT 0 CHECK(blocked IN (0,1))")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, action TEXT NOT NULL, user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS customer_sessions (
            token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            expires INTEGER NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS customer_sessions_user ON customer_sessions(user_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS customer_profiles (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            display_name TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en'
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS customer_favorites (
            user_id INTEGER NOT NULL REFERENCES users(id),
            place TEXT NOT NULL,
            PRIMARY KEY(user_id,place)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS customer_activities (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL, activity_date TEXT NOT NULL,
            distance_km REAL NOT NULL, elevation_m INTEGER NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS activities_user ON customer_activities(user_id)")
        conn.execute("SELECT id, email, role, plan FROM users LIMIT 0")
    return True
