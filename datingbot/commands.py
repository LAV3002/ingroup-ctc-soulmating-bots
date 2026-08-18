from __future__ import annotations

import logging
from collections.abc import Iterable

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


USER_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Начать знакомство"),
    BotCommand("profile", "Открыть мою анкету"),
    BotCommand("browse", "Смотреть людей"),
    BotCommand("cancel", "Закрыть черновик"),
]

ADMIN_ACTIONS: list[BotCommand] = [
    BotCommand("first", "Этап 1: открыть анкеты"),
    BotCommand("dump", "Выгрузка анкет, лайков и метчей"),
    BotCommand("reset", "Полный сброс"),
    BotCommand("help", "Справка администратора"),
]
ADMIN_COMMANDS = USER_COMMANDS + ADMIN_ACTIONS


async def setup_commands(bot, admin_ids: Iterable[int]) -> None:
    """Меню команд: для всех — пользовательское, для админов — администраторское."""
    try:
        await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    except TelegramError as exc:
        logger.warning("Не удалось установить пользовательское меню: %r", exc)
    sent = 0
    for uid in admin_ids:
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=uid))
            sent += 1
        except TelegramError as exc:
            logger.warning("Не удалось установить меню админа для uid=%s: %r", uid, exc)
    logger.info("Меню установлено: пользователи + администраторы (%d чатов)", sent)
