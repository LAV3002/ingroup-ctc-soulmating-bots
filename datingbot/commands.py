from __future__ import annotations

import logging
from collections.abc import Iterable

from telegram import BotCommand, BotCommandScopeChat
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


ADMIN_COMMANDS: list[BotCommand] = [
    BotCommand("first", "Этап 1: открыть анкеты"),
    BotCommand("second", "Подобрать и разослать метчи"),
    BotCommand("dump", "Выгрузка анкет и пар"),
    BotCommand("reset", "Полный сброс"),
    BotCommand("help", "Справка администратора"),
]


async def setup_admin_menu(bot, admin_ids: Iterable[int]) -> int:
    sent = 0
    for uid in admin_ids:
        try:
            await bot.set_my_commands(
                ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=uid)
            )
            sent += 1
        except TelegramError as exc:
            logger.warning("Не удалось установить меню админа для uid=%s: %r", uid, exc)
    logger.info("Меню администратора установлено для %d чатов", sent)
    return sent
