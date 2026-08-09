from __future__ import annotations

import logging

from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = ""
    update_id = getattr(update, "update_id", None)
    if update_id is not None:
        info = f"update_id={update_id}"
        user = getattr(update, "effective_user", None)
        chat = getattr(update, "effective_chat", None)
        if user is not None:
            info += f" uid={user.id}"
        if chat is not None:
            info += f" chat={chat.id}"
    logger.error("Ошибка при обработке (%s): %s", info, context.error, exc_info=True)
