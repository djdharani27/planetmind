from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    app_name: str = "PlanetMind AI"
    app_version: str = "0.1.0"
    debug: bool = True

    backend_dir: Path = Path(__file__).resolve().parent
    project_root: Path = backend_dir.parent
    storage_dir: Path = project_root / "storage"
    uploads_dir: Path = storage_dir / "uploads"
    processed_dir: Path = storage_dir / "processed"
    cache_dir: Path = storage_dir / "cache"
    sqlite_dir: Path = project_root / "sqlite"
    sqlite_path: Path = sqlite_dir / "planetmind.db"

    log_level: str = "INFO"
    log_file: Path = project_root / "planetmind.log"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": str(Path(__file__).resolve().parent.parent / ".env"), "extra": "ignore"}


settings = Settings()
