from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Маскируем только номера телефонов с ведущим '+', чтобы не задеть
# user_id/chat_id (PII-safety net: в лог-вызовах мы PII и так не пишем).
_PHONE_RE = re.compile(r"\+\d[\d\- ]{5,}\d")

_CONSOLE_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_FILE_FMT = "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# Шумные библиотеки — на WARNING.
_NOISY_LIBS = ("telegram", "httpx", "httpcore", "aiolimiter", "APScheduler")


class RedactingFilter(logging.Filter):
    """Маскирует телефоны и секреты в тексте логов."""

    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self._secrets = tuple(s for s in secrets if s)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _PHONE_RE.sub("[PHONE]", message)
        for secret in self._secrets:
            redacted = redacted.replace(secret, "[SECRET]")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def describe_user(p: object) -> str:
    """PII-безопасное описание участника для логов: без имени/@username/телефона."""
    return (
        f"uid={getattr(p, 'user_id', '?')} "
        f"chat={getattr(p, 'chat_id', '?')}"
    )


def setup_logging(
    *,
    level: str = "INFO",
    log_file: str = "logs/datingbot.log",
    max_bytes: int = 1_000_000,
    backup_count: int = 5,
    secret: str = "",
) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(logging.DEBUG)

    redactor = RedactingFilter(secrets=(secret,))

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_FMT))
    console.addFilter(redactor)
    root.addHandler(console)

    path = Path(log_file)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATE_FMT))
    file_handler.addFilter(redactor)
    root.addHandler(file_handler)

    for lib in _NOISY_LIBS:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger("datingbot").setLevel(logging.DEBUG)
