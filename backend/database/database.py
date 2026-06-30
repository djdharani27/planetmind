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

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {db_path}")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
