from __future__ import annotations

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import MAX_SYMPATHIES
from regabot import texts
from regabot.constants import Stage
from regabot.keyboards import sympathy_table_keyboard
from regabot.state import find_badge_in_table, find_tables_of_user, get_table

logger = logging.getLogger(__name__)

ENTER = 0
CHOOSE = 1


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    uid = user.id if user else None
    return f"uid={uid} chat={chat.id if chat else None}"


async def _enter_sympathy(
    update: Update, context: ContextTypes.DEFAULT_TYPE, scope: str
) -> int:
    user = update.effective_user
    table = get_table(context.bot_data, scope)
    if table.stage != Stage.SECOND:
        logger.info("/sympathy отклонён: стол %s на этапе %s", scope, table.stage)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=texts.sympathy_closed(scope)
        )
        return ConversationHandler.END

    badge = find_badge_in_table(table, user.id) if user else None
    if badge is None:
        logger.info("/sympathy отклонён: не зарегистрирован за столом %s", scope)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=texts.NOT_REGISTERED)
        return ConversationHandler.END
    context.user_data["sym"] = {"table": scope, "badge": badge, "entries": []}
    logger.info("Выбор симпатий начат: стол=%s badge=%s %s", scope, badge, _who(update))
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=texts.sympathy_intro(MAX_SYMPATHIES)
    )
    return ENTER


async def sympathy_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.debug("/sympathy от %s", _who(update))
    user_tables = find_tables_of_user(context.bot_data, user.id) if user else []
    if not user_tables:
        logger.info("/sympathy отклонён: нигде не зарегистрирован, %s", _who(update))
        await update.message.reply_text(texts.NOT_REGISTERED)
        return ConversationHandler.END

    arg = context.args[0].strip().lower() if context.args else None
    if arg:
        scope = next((t for t, _ in user_tables if t == arg), None)
        if scope is None:
            logger.info("/sympathy отклонён: не зарегистрирован за столом %s", arg)
            await update.message.reply_text(texts.sympathy_wrong_table(arg))
            return ConversationHandler.END
        return await _enter_sympathy(update, context, scope)

    if len(user_tables) == 1:
        return await _enter_sympathy(update, context, user_tables[0][0])

    tags = [t for t, _ in user_tables]
    logger.info("/sympathy: неоднозначно, показ кнопок, столы=%s", tags)
    await update.message.reply_text(
        texts.sympathy_ambiguous(tags), reply_markup=sympathy_table_keyboard(tags)
    )
    return CHOOSE


async def on_pick_sympathy_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    user = update.effective_user
    tag = cq.data.split(":", 1)[1]
    user_tables = find_tables_of_user(context.bot_data, user.id) if user else []
    scope = next((t for t, _ in user_tables if t == tag), None)
    try:
        await cq.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass
    if scope is None:
        logger.info("/sympathy (кнопка): не зарегистрирован за столом %s", tag)
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=texts.sympathy_wrong_table(tag)
        )
        return ConversationHandler.END
    return await _enter_sympathy(update, context, scope)


def _parse_entry(raw: str) -> int | None:
    parts = raw.replace(",", " ").split()
    if len(parts) != 1:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


def add_entry(
    entries: list[tuple[int, int]], target: int, priority: int
) -> list[tuple[int, int]]:
    updated = [(t, p) for (t, p) in entries if t != target]
    updated.append((target, priority))
    updated.sort(key=lambda tp: -tp[1])
    return updated


async def on_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "sym" not in context.user_data:
        return ConversationHandler.END
    data = context.user_data["sym"]
    table = get_table(context.bot_data, data["table"])
    raw = (update.message.text or "").strip()
    parsed = _parse_entry(raw)
    if parsed is None:
        logger.warning("Неверный формат '%s' стол=%s badge=%s", raw, data["table"], data["badge"])
        await update.message.reply_text(texts.SYMPATHY_FORMAT)
        return ENTER

    target = parsed
    if target not in table.registrations:
        logger.warning(
            "Неизвестный номер %d стол=%s badge=%s", target, data["table"], data["badge"]
        )
        await update.message.reply_text(texts.SYMPATHY_TARGET_UNKNOWN)
        return ENTER
    if target == data["badge"]:
        logger.warning("Симпатия на себя стол=%s badge=%s", data["table"], data["badge"])
        await update.message.reply_text(texts.SYMPATHY_SELF)
        return ENTER

    priority = 4 - len(data["entries"])
    entries = add_entry(data["entries"], target, priority)
    data["entries"] = entries
    logger.info(
        "Симпатия: стол=%s badge=%s -> target=%d prio=%d",
        data["table"], data["badge"], target, priority,
    )

    if len(entries) >= MAX_SYMPATHIES:
        return await _finish(update, context)

    await update.message.reply_text(texts.sympathy_progress(entries, MAX_SYMPATHIES))
    return ENTER


async def _finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("sym", None)
    if data is None:
        return ConversationHandler.END
    table = get_table(context.bot_data, data["table"])
    table.sympathies[data["badge"]] = list(data["entries"])
    logger.info(
        "Симпатии сохранены: стол=%s badge=%s всего=%d",
        data["table"], data["badge"], len(data["entries"]),
    )
    await update.message.reply_text(texts.sympathy_saved(data["entries"]))
    return ConversationHandler.END


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("/sympathy_done симпатии от %s", _who(update))
    return await _finish(update, context)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.get("sym")
    if data is not None:
        logger.info("Очистка симпатий стол=%s badge=%s", data["table"], data["badge"])
        data["entries"] = []
    await update.message.reply_text(texts.SYMPATHY_CLEARED)
    return ENTER


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Отмена симпатий: %s", _who(update))
    context.user_data.pop("sym", None)
    await update.message.reply_text(texts.SYMPATHY_CANCELLED)
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("sympathy", sympathy_entry, filters=filters.ChatType.PRIVATE)],
        states={
            CHOOSE: [CallbackQueryHandler(on_pick_sympathy_table, pattern="^sym:")],
            ENTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_entry)],
        },
        fallbacks=[
            CommandHandler("sympathy", sympathy_entry),
            CommandHandler("sympathy_done", done),
            CommandHandler("clear", clear),
            CommandHandler("cancel", cancel),
        ],
        name="sympathy_conv",
        persistent=True,
        per_message=False,
    )
