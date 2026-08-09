from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str) -> frozenset[int]:
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            continue
    return frozenset(result)


TELEGRAM_BOT_TOKEN: str = os.getenv("DATING_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")

ADMIN_USER_IDS: frozenset[int] = _parse_ids(os.getenv("DATING_ADMIN_IDS", ""))

PERSISTENCE_FILE: str = os.getenv("DATING_PERSISTENCE_FILE", "datingbot_data.pickle")

# Подбор метчей
MATCHES_PER_USER: int = 1
MIN_AGE: int = int(os.getenv("DATING_MIN_AGE", "18"))
MAX_AGE: int = int(os.getenv("DATING_MAX_AGE", "99"))
AGE_PROXIMITY_BONUS: float = float(os.getenv("DATING_AGE_BONUS", "0.5"))
AGE_PENALTY_PER_YEAR: float = float(os.getenv("DATING_AGE_PENALTY", "0.1"))

# Логирование
LOG_LEVEL: str = os.getenv("DATING_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO"))
LOG_FILE: str = os.getenv("DATING_LOG_FILE", "logs/datingbot.log")
LOG_MAX_BYTES: int = int(os.getenv("DATING_LOG_MAX_BYTES", os.getenv("LOG_MAX_BYTES", "1000000")))
LOG_BACKUP_COUNT: int = int(
    os.getenv("DATING_LOG_BACKUP_COUNT", os.getenv("LOG_BACKUP_COUNT", "5"))
)

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def assets_dir() -> Path:
    return _ASSETS_DIR


def validate() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("DATING_BOT_TOKEN (или TELEGRAM_BOT_TOKEN) не задан в .env")
    if not ADMIN_USER_IDS:
        raise RuntimeError("DATING_ADMIN_IDS не задан в .env")
