from __future__ import annotations

import logging
from collections.abc import Iterable

from telegram import BotCommand, BotCommandScopeChat
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


ADMIN_COMMANDS: list[BotCommand] = [
    BotCommand("use", "Выбрать активный стол"),
    BotCommand("first", "Этап 1: открыть регистрацию"),
    BotCommand("second", "Этап 2: открыть выбор симпатий"),
    BotCommand("third", "Этап 3: взаимные симпатии"),
    BotCommand("love", "Разослать контакты метчей"),
    BotCommand("love_force", "Повторно разослать контакты"),
    BotCommand("reset", "Сбросить активный стол"),
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
