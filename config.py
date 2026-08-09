from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_tables(raw: str) -> dict[int, tuple[str, ...]]:
    """Формат: user_id:tag1,tag2;user_id2:tag1 (через ';' между админами)."""
    result: dict[int, tuple[str, ...]] = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        uid_str, tags_str = entry.split(":", 1)
        try:
            uid = int(uid_str.strip())
        except ValueError:
            continue
        tags = tuple(t.strip().lower() for t in tags_str.split(",") if t.strip())
        if tags:
            result[uid] = tags
    return result


TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

ADMIN_TABLES: dict[int, tuple[str, ...]] = _parse_admin_tables(os.getenv("ADMIN_TABLES", ""))
ADMIN_USER_IDS: frozenset[int] = frozenset(ADMIN_TABLES.keys())

TABLE_TAGS: tuple[str, ...] = tuple(
    t.strip() for t in os.getenv("TABLE_TAGS", "converse,art").split(",") if t.strip()
)

PERSISTENCE_FILE: str = os.getenv("PERSISTENCE_FILE", "regabot_data.pickle")

MAX_SYMPATHIES: int = int(os.getenv("MAX_SYMPATHIES", "3"))

# Логирование
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "logs/regabot.log")
LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "1000000"))
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Идеи для первой встречи грузятся из внешнего файла (по тегу стола).
# Формат файла: блок [tag], под ним строки начинаются с '-'. См. meeting_ideas.txt.
def _load_meeting_ideas(path: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    if not os.path.isfile(path):
        return result
    current: str | None = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1].strip().lower()
                result.setdefault(current, [])
                continue
            if line.startswith("-"):
                item = line.lstrip("-").strip()
                if current is not None and item:
                    result[current].append(item)
    return result


_DEFAULT_IDEAS_FILE = str(Path(__file__).resolve().parent / "meeting_ideas.txt")
MEETING_IDEAS_FILE: str = os.getenv("MEETING_IDEAS_FILE", _DEFAULT_IDEAS_FILE)
MEETING_IDEAS: dict[str, list[str]] = _load_meeting_ideas(MEETING_IDEAS_FILE)


def validate() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")
    if not ADMIN_TABLES:
        raise RuntimeError("ADMIN_TABLES не задан в .env")
    if not TABLE_TAGS:
        raise RuntimeError("TABLE_TAGS не задан в .env")
    for uid, tags in ADMIN_TABLES.items():
        for tag in tags:
            if tag not in TABLE_TAGS:
                raise RuntimeError(
                    f"ADMIN_TABLES: администратор {uid} назначен на неизвестный стол '{tag}'"
                )
