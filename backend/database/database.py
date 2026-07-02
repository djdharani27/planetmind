import sqlite3
from pathlib import Path
from backend.config import settings
from backend.logging_config import logger


def get_db_path() -> Path:
    settings.sqlite_dir.mkdir(parents=True, exist_ok=True)
    return settings.sqlite_path


def init_db() -> None:
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            processing_status TEXT NOT NULL DEFAULT 'uploaded',
            storage_path TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operator',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            metadata TEXT DEFAULT '{}'
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_session
        ON conversations(session_id, timestamp)
    """)

    conn.commit()

    _seed_default_user(conn)

    conn.close()
    logger.info(f"Database initialized at {db_path}")


def _seed_default_user(conn):
    existing = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    if existing == 0:
        from backend.auth import hash_password
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), "admin"),
        )
        conn.commit()
        logger.info("Default user created: admin / admin123")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
