import logging
import sys
from pathlib import Path
from backend.config import settings


def setup_logging() -> logging.Logger:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("planetmind")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()
