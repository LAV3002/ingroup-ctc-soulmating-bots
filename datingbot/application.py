from __future__ import annotations

import logging

from telegram.ext import AIORateLimiter, ApplicationBuilder, PicklePersistence

from datingbot import config as dating_config
from datingbot.commands import setup_commands
from datingbot.handlers.admin import build_handlers as admin_handlers
from datingbot.handlers.browse import build_conversation as browse_conv
from datingbot.handlers.errors import on_error
from datingbot.handlers.registration import build_conversation as reg_conv
from datingbot.logging_setup import setup_logging

logger = logging.getLogger(__name__)


async def _post_init(application) -> None:
    await setup_commands(application.bot, dating_config.ADMIN_USER_IDS)


def build_application():
    dating_config.validate()
    setup_logging(
        level=dating_config.LOG_LEVEL,
        log_file=dating_config.LOG_FILE,
        max_bytes=dating_config.LOG_MAX_BYTES,
        backup_count=dating_config.LOG_BACKUP_COUNT,
        secret=dating_config.TELEGRAM_BOT_TOKEN,
    )
    logger.info("DatingBot startup")

    persistence = PicklePersistence(filepath=dating_config.PERSISTENCE_FILE)
    application = (
        ApplicationBuilder()
        .token(dating_config.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .rate_limiter(AIORateLimiter())
        .post_init(_post_init)
        .build()
    )

    application.add_handler(reg_conv())
    application.add_handler(browse_conv())
    for handler in admin_handlers():
        application.add_handler(handler)
    application.add_error_handler(on_error)

    logger.info("Обработчики зарегистрированы, приложение готово")
    return application
