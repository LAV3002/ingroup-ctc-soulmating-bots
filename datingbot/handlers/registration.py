from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from datingbot import config, texts
from datingbot.constants import GENDERS, LOOKING_FOR, Stage
from datingbot.keyboards import (
    browse_keyboard,
    gender_keyboard,
    looking_for_keyboard,
    verification_keyboard,
)
from datingbot.logging_setup import describe_user
from datingbot.models import Profile
from datingbot.state import get_profile, get_stage, remember_verify_msg, save_profile

logger = logging.getLogger(__name__)

NAME, GENDER, AGE, LOOKING, PHOTO, HOBBIES, DREAM = range(7)


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"uid={user.id if user else None} chat={chat.id if chat else None}"


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.debug("/start от %s", _who(update))
    stage = get_stage(context.bot_data)
    if stage != Stage.FIRST:
        logger.info("/start отклонён: этап=%s %s", stage, _who(update))
        await update.message.reply_text(texts.START_CLOSED, parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    existing = get_profile(context.bot_data, user.id) if user else None
    if existing is not None:
        if existing.verified:
            await update.message.reply_text(
                texts.start_open(True),
                parse_mode=ParseMode.HTML,
                reply_markup=browse_keyboard(),
            )
        else:
            await update.message.reply_text(
                texts.PROFILE_PENDING, parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END

    context.user_data["dating"] = {
        "user_id": user.id if user else 0,
        "chat_id": update.effective_chat.id,
        "username": user.username if user else None,
        "photo_file_id": None,
    }
    logger.info("Начата анкета: %s", _who(update))
    await update.message.reply_text(texts.start_open(False), parse_mode=ParseMode.HTML)
    return NAME


async def on_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text(texts.NAME_EMPTY, parse_mode=ParseMode.HTML)
        return NAME
    context.user_data["dating"]["name"] = name
    await update.message.reply_text(
        texts.ASK_GENDER,
        parse_mode=ParseMode.HTML,
        reply_markup=gender_keyboard(),
    )
    return GENDER


async def on_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    value = cq.data.split(":", 1)[1]
    if value not in GENDERS:
        return GENDER
    context.user_data["dating"]["gender"] = value
    await cq.edit_message_text(texts.ASK_AGE, parse_mode=ParseMode.HTML)
    return AGE


async def on_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    try:
        age = int(raw)
    except ValueError:
        await update.message.reply_text(texts.AGE_INVALID, parse_mode=ParseMode.HTML)
        return AGE
    if age < config.MIN_AGE or age > config.MAX_AGE:
        await update.message.reply_text(
            texts.AGE_OUT_OF_RANGE.format(min=config.MIN_AGE, max=config.MAX_AGE),
            parse_mode=ParseMode.HTML,
        )
        return AGE
    context.user_data["dating"]["age"] = age
    await update.message.reply_text(
        texts.ASK_LOOKING_FOR,
        parse_mode=ParseMode.HTML,
        reply_markup=looking_for_keyboard(),
    )
    return LOOKING


async def on_looking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    value = cq.data.split(":", 1)[1]
    if value not in LOOKING_FOR:
        return LOOKING
    context.user_data["dating"]["looking_for"] = value
    await cq.edit_message_text(texts.ASK_PHOTO, parse_mode=ParseMode.HTML)
    return PHOTO


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photos = update.message.photo
    if not photos:
        await update.message.reply_text(texts.PHOTO_INVALID, parse_mode=ParseMode.HTML)
        return PHOTO
    context.user_data["dating"]["photo_file_id"] = photos[-1].file_id
    logger.debug("Фото получено от %s", _who(update))
    await update.message.reply_text(
        f"{texts.PHOTO_SAVED_ACK}\n\n{texts.ASK_HOBBIES}",
        parse_mode=ParseMode.HTML,
    )
    return HOBBIES


async def photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(texts.PHOTO_INVALID, parse_mode=ParseMode.HTML)
    return PHOTO


async def on_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hobbies = (update.message.text or "").strip()
    if not hobbies:
        await update.message.reply_text(texts.TEXT_EMPTY, parse_mode=ParseMode.HTML)
        return HOBBIES
    context.user_data["dating"]["hobbies"] = hobbies
    await update.message.reply_text(texts.ASK_DREAM, parse_mode=ParseMode.HTML)
    return DREAM


async def on_dream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dream = (update.message.text or "").strip()
    if not dream:
        await update.message.reply_text(texts.TEXT_EMPTY, parse_mode=ParseMode.HTML)
        return DREAM
    data = context.user_data["dating"]
    data["dream"] = dream
    await _finalize(update, context)
    return ConversationHandler.END


async def _finalize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.user_data.pop("dating", None)
    if data is None:
        return
    user = update.effective_user
    profile = Profile(
        user_id=data["user_id"],
        chat_id=data["chat_id"],
        name=data["name"],
        username=user.username if user else data.get("username"),
        gender=data["gender"],
        age=data["age"],
        looking_for=data["looking_for"],
        hobbies=data["hobbies"],
        dream=data["dream"],
        photo_file_id=data.get("photo_file_id"),
    )
    save_profile(context.bot_data, profile)
    logger.info("Анкета сохранена: %s", describe_user(profile))
    await context.bot.send_message(
        chat_id=profile.chat_id,
        text=texts.profile_saved(profile),
        parse_mode=ParseMode.HTML,
    )
    await _send_admin_verification(context, profile)


async def _send_admin_verification(
    context: ContextTypes.DEFAULT_TYPE, profile: Profile
) -> None:
    """Рассылает администраторам карточку анкеты с кнопками верификации."""
    card = texts.admin_verification_card(profile)
    markup = verification_keyboard(profile.user_id)
    admin_ids = sorted(config.ADMIN_USER_IDS)
    tasks = [
        (
            context.bot.send_photo(
                chat_id=uid,
                photo=profile.photo_file_id,
                caption=card,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
            if profile.photo_file_id
            else context.bot.send_message(
                chat_id=uid,
                text=card,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        )
        for uid in admin_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    delivered = 0
    for uid, result in zip(admin_ids, results, strict=True):
        if isinstance(result, BaseException):  # noqa: BLE001
            logger.warning("Карточка верификации не доставлена админу uid=%s: %r", uid, result)
        else:
            delivered += 1
            remember_verify_msg(context.bot_data, profile.user_id, uid, result.message_id)
    logger.info(
        "Карточки верификации разосланы: доставлено=%d из %d, uid=%s",
        delivered,
        len(admin_ids),
        profile.user_id,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Анкета отменена: %s", _who(update))
    context.user_data.pop("dating", None)
    await update.message.reply_text(
        texts.REGISTRATION_CANCELLED, parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_entry, filters=filters.ChatType.PRIVATE)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_name)],
            GENDER: [CallbackQueryHandler(on_gender, pattern="^gen:")],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_age)],
            LOOKING: [CallbackQueryHandler(on_looking, pattern="^lf:")],
            PHOTO: [
                MessageHandler(filters.PHOTO, on_photo),
                MessageHandler(filters.ALL & ~filters.COMMAND, photo_fallback),
            ],
            HOBBIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_hobbies)],
            DREAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_dream)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="dating_reg",
        persistent=True,
        per_message=False,
    )
