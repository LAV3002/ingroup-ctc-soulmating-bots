from __future__ import annotations

import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TABLE_TAGS
from regabot import texts
from regabot.constants import Stage
from regabot.keyboards import contact_keyboard
from regabot.logging_setup import describe_participant
from regabot.models import Participant
from regabot.state import (
    find_badge_in_table,
    find_tables_of_user,
    get_profile,
    get_table,
    set_profile,
)

logger = logging.getLogger(__name__)

NAME, CONTACT, TABLE, BADGE = range(4)


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    uid = user.id if user else None
    return f"uid={uid} chat={chat.id if chat else None}"


def _open_tables(bot_data: dict) -> list[str]:
    return [t for t in TABLE_TAGS if get_table(bot_data, t).stage == Stage.FIRST]


# --- /start: приветствие ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.debug("/start от %s", _who(update))
    open_tags = _open_tables(context.bot_data)
    my_tables = [t for t, _ in find_tables_of_user(context.bot_data, user.id)] if user else []
    has_profile = get_profile(context.bot_data, user.id) is not None if user else False
    await update.message.reply_text(texts.start_hello(open_tags, my_tables, has_profile))


# --- /reg_for_table: регистрация на текущую сессию ---
async def _select_table(update: Update, context: ContextTypes.DEFAULT_TYPE, tag: str) -> int:
    user = update.effective_user
    reg = context.user_data["reg"]
    if tag not in TABLE_TAGS:
        logger.warning("Неверный тег стола '%s' от %s", tag, _who(update))
        await update.message.reply_text(texts.table_invalid(", ".join(TABLE_TAGS)))
        return TABLE
    table = get_table(context.bot_data, tag)
    if table.stage != Stage.FIRST:
        logger.info("Стол %s не на этапе FIRST для %s", tag, _who(update))
        open_tags = ", ".join(_open_tables(context.bot_data))
        await update.message.reply_text(texts.table_closed(tag, open_tags))
        return TABLE
    if user is not None and find_badge_in_table(table, user.id) is not None:
        logger.info("Уже зарегистрирован за столом %s: %s", tag, _who(update))
        await update.message.reply_text(texts.already_at_table(tag))
        return ConversationHandler.END
    reg["table_tag"] = tag
    logger.debug("Тег стола=%s от %s", tag, _who(update))
    await update.message.reply_text(texts.ASK_BADGE, reply_markup=ReplyKeyboardRemove())
    return BADGE


async def reg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.debug("/reg_for_table от %s", _who(update))

    open_tags = _open_tables(context.bot_data)
    if not open_tags:
        logger.info("Открытых столов нет: %s", _who(update))
        await update.message.reply_text(texts.no_open_tables())
        return ConversationHandler.END

    reg: dict = {"username": user.username if user else None}
    context.user_data["reg"] = reg
    arg = context.args[0].strip().lower() if context.args else None

    profile = get_profile(context.bot_data, user.id) if user else None
    if profile is not None:
        reg["name"] = profile.name
        reg["phone"] = profile.phone
        logger.info("Регистрация (есть профиль): %s", _who(update))
        if arg in TABLE_TAGS:
            return await _select_table(update, context, arg)
        await update.message.reply_text(texts.ask_table(", ".join(open_tags)))
        return TABLE

    if arg in TABLE_TAGS:
        reg["pending_table"] = arg
    logger.info("Регистрация (новый профиль): %s", _who(update))
    await update.message.reply_text(texts.ASK_NAME)
    return NAME


async def on_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    logger.debug("Имя получено от %s", _who(update))
    if not name:
        logger.warning("Пустое имя от %s", _who(update))
        await update.message.reply_text(texts.NAME_EMPTY)
        return NAME
    context.user_data["reg"]["name"] = name
    await update.message.reply_text(
        texts.ASK_CONTACT.format(name=name), reply_markup=contact_keyboard()
    )
    return CONTACT


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    user = update.effective_user
    if contact is None:
        await update.message.reply_text(texts.CONTACT_MISSING)
        return CONTACT
    if user is not None and contact.user_id is not None and contact.user_id != user.id:
        logger.warning("Контакт не свой: uid=%s contact_uid=%s", user.id, contact.user_id)
        await update.message.reply_text(texts.CONTACT_NOT_YOURS)
        return CONTACT

    reg = context.user_data["reg"]
    reg["phone"] = contact.phone_number
    reg["username"] = user.username if user else None
    logger.debug("Контакт получен от %s", _who(update))
    pending = reg.pop("pending_table", None)
    if pending in TABLE_TAGS:
        return await _select_table(update, context, pending)
    open_tags = ", ".join(_open_tables(context.bot_data))
    await update.message.reply_text(texts.ask_table(open_tags), reply_markup=ReplyKeyboardRemove())
    return TABLE


async def contact_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("Ожидался контакт, получено иное от %s", _who(update))
    await update.message.reply_text(texts.CONTACT_MISSING, reply_markup=contact_keyboard())
    return CONTACT


async def on_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tag = (update.message.text or "").strip().lower()
    return await _select_table(update, context, tag)


async def on_badge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    try:
        badge = int(raw)
    except ValueError:
        logger.warning("Неверный номер бейджа '%s' от %s", raw, _who(update))
        await update.message.reply_text(texts.BADGE_INVALID)
        return BADGE
    if badge <= 0:
        logger.warning("Неверный номер бейджа %d от %s", badge, _who(update))
        await update.message.reply_text(texts.BADGE_INVALID)
        return BADGE

    reg = context.user_data["reg"]
    table = get_table(context.bot_data, reg["table_tag"])
    if badge in table.registrations:
        logger.warning("Номер %d занят за столом %s, %s", badge, reg["table_tag"], _who(update))
        await update.message.reply_text(texts.BADGE_TAKEN)
        return BADGE

    user = update.effective_user
    participant = Participant(
        chat_id=update.effective_chat.id,
        user_id=user.id if user else 0,
        name=reg["name"],
        phone=reg["phone"],
        username=reg.get("username"),
        table_tag=reg["table_tag"],
        badge=badge,
    )
    table.registrations[badge] = participant
    if user is not None:
        set_profile(context.bot_data, user.id, reg["name"], reg["phone"], reg.get("username"))
    context.user_data.pop("reg", None)
    logger.info(
        "Регистрация завершена: стол=%s %s",
        reg["table_tag"], describe_participant(participant),
    )
    await update.message.reply_text(texts.registered(participant))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Регистрация отменена: %s", _who(update))
    context.user_data.pop("reg", None)
    await update.message.reply_text(
        texts.REGISTRATION_CANCELLED, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def build_start_handler() -> CommandHandler:
    return CommandHandler("start", cmd_start, filters=filters.ChatType.PRIVATE)


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("reg_for_table", reg_entry, filters=filters.ChatType.PRIVATE)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_name)],
            CONTACT: [
                MessageHandler(filters.CONTACT, on_contact),
                MessageHandler(filters.ALL, contact_fallback),
            ],
            TABLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_table)],
            BADGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_badge)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="reg_conv",
        persistent=True,
        per_message=False,
    )
