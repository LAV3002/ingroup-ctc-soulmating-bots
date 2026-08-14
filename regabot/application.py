from __future__ import annotations

import logging

from telegram.ext import AIORateLimiter, ApplicationBuilder, PicklePersistence

import config
from regabot.commands import setup_admin_menu
from regabot.handlers.admin import build_handlers as admin_handlers
from regabot.handlers.errors import on_error
from regabot.handlers.registration import build_conversation as reg_conv
from regabot.handlers.registration import build_start_handler as start_handler
from regabot.handlers.sympathy import build_conversation as sympathy_conv
from regabot.logging_setup import setup_logging

logger = logging.getLogger(__name__)


async def _post_init(application) -> None:
    await setup_admin_menu(application.bot, config.ADMIN_USER_IDS)


def build_application():
    config.validate()
    setup_logging(
        level=config.LOG_LEVEL,
        log_file=config.LOG_FILE,
        max_bytes=config.LOG_MAX_BYTES,
        backup_count=config.LOG_BACKUP_COUNT,
        secret=config.TELEGRAM_BOT_TOKEN,
    )
    logger.info("RegaBot startup")

    missing_ideas = [t for t in config.TABLE_TAGS if not config.MEETING_IDEAS.get(t)]
    if missing_ideas:
        logger.warning("Без идей для встречи остались столы: %s", ", ".join(missing_ideas))

    persistence = PicklePersistence(filepath=config.PERSISTENCE_FILE)
    application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .rate_limiter(AIORateLimiter())
        .post_init(_post_init)
        .build()
    )

    application.add_handler(start_handler())
    application.add_handler(reg_conv())
    application.add_handler(sympathy_conv())
    for handler in admin_handlers():
        application.add_handler(handler)
    application.add_error_handler(on_error)

    logger.info("Обработчики зарегистрированы, приложение готово")
    return application
