from __future__ import annotations

import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.error import BadRequest
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
    contact_keyboard,
    gender_keyboard,
    looking_for_keyboard,
    photo_choice_keyboard,
    question_keyboard,
    skip_photo_keyboard,
)
from datingbot.logging_setup import describe_user
from datingbot.models import Profile
from datingbot.questions import TEST_QUESTIONS, photo_path
from datingbot.state import get_profile, get_stage, save_profile

logger = logging.getLogger(__name__)

NAME, CONTACT, GENDER, AGE, LOOKING, PHOTO, HOBBIES, DREAM, TEST = range(9)

PHOTO_CACHE_KEY = "dating_photo_cache"


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"uid={user.id if user else None} chat={chat.id if chat else None}"


async def _send_cached_photo(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, filename: str, caption: str
) -> None:
    cache = context.bot_data.setdefault(PHOTO_CACHE_KEY, {})
    file_id = cache.get(filename)
    if file_id:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
            return
        except BadRequest:
            cache.pop(filename, None)
    with open(photo_path(filename), "rb") as fh:
        msg = await context.bot.send_photo(chat_id=chat_id, photo=fh, caption=caption)
    if msg.photo:
        cache[filename] = msg.photo[-1].file_id


async def _present_question(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, question
) -> None:
    if question.kind == "text":
        await context.bot.send_message(
            chat_id=chat_id, text=question.text, reply_markup=question_keyboard(question)
        )
        return
    for i, fname in enumerate(question.photos):
        await _send_cached_photo(context, chat_id, fname, caption=f"Вариант {i + 1}")
    await context.bot.send_message(
        chat_id=chat_id, text=question.text, reply_markup=photo_choice_keyboard(question)
    )


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.debug("/start от %s", _who(update))
    stage = get_stage(context.bot_data)
    if stage != Stage.FIRST:
        logger.info("/start отклонён: этап=%s %s", stage, _who(update))
        await update.message.reply_text(texts.START_CLOSED)
        return ConversationHandler.END

    existing = get_profile(context.bot_data, user.id) if user else None
    if existing is not None:
        await update.message.reply_text(texts.start_open(True))
        return ConversationHandler.END

    context.user_data["dating"] = {
        "user_id": user.id if user else 0,
        "chat_id": update.effective_chat.id,
        "username": user.username if user else None,
        "photo_file_id": None,
        "answers": {},
        "q_index": 0,
    }
    logger.info("Начата анкета: %s", _who(update))
    await update.message.reply_text(texts.start_open(False))
    return NAME


async def on_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text(texts.NAME_EMPTY)
        return NAME
    context.user_data["dating"]["name"] = name
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
        logger.warning("Чужой контакт: uid=%s contact_uid=%s", user.id, contact.user_id)
        await update.message.reply_text(texts.CONTACT_NOT_YOURS)
        return CONTACT

    data = context.user_data["dating"]
    data["phone"] = contact.phone_number
    if user is not None:
        data["username"] = user.username
    logger.debug("Контакт получен от %s", _who(update))
    await update.message.reply_text(texts.ASK_GENDER, reply_markup=gender_keyboard())
    return GENDER


async def contact_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(texts.CONTACT_MISSING, reply_markup=contact_keyboard())
    return CONTACT


async def on_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    value = cq.data.split(":", 1)[1]
    if value not in GENDERS:
        return GENDER
    context.user_data["dating"]["gender"] = value
    await cq.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texts.ASK_AGE)
    return AGE


async def on_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    try:
        age = int(raw)
    except ValueError:
        await update.message.reply_text(texts.AGE_INVALID)
        return AGE
    if age < config.MIN_AGE or age > config.MAX_AGE:
        await update.message.reply_text(
            texts.AGE_OUT_OF_RANGE.format(min=config.MIN_AGE, max=config.MAX_AGE)
        )
        return AGE
    context.user_data["dating"]["age"] = age
    await update.message.reply_text(texts.ASK_LOOKING_FOR, reply_markup=looking_for_keyboard())
    return LOOKING


async def on_looking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    value = cq.data.split(":", 1)[1]
    if value not in LOOKING_FOR:
        return LOOKING
    context.user_data["dating"]["looking_for"] = value
    await cq.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts.ASK_PHOTO,
        reply_markup=skip_photo_keyboard(),
    )
    return PHOTO


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photos = update.message.photo
    if not photos:
        await update.message.reply_text(texts.PHOTO_INVALID, reply_markup=skip_photo_keyboard())
        return PHOTO
    context.user_data["dating"]["photo_file_id"] = photos[-1].file_id
    logger.debug("Фото получено от %s", _who(update))
    await update.message.reply_text("Фото сохранено!\n\n" + texts.ASK_HOBBIES)
    return HOBBIES


async def on_photo_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    await cq.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=texts.ASK_HOBBIES)
    return HOBBIES


async def photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(texts.PHOTO_INVALID, reply_markup=skip_photo_keyboard())
    return PHOTO


async def on_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hobbies = (update.message.text or "").strip()
    if not hobbies:
        await update.message.reply_text(texts.TEXT_EMPTY)
        return HOBBIES
    context.user_data["dating"]["hobbies"] = hobbies
    await update.message.reply_text(texts.ASK_DREAM)
    return DREAM


async def on_dream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dream = (update.message.text or "").strip()
    if not dream:
        await update.message.reply_text(texts.TEXT_EMPTY)
        return DREAM
    context.user_data["dating"]["dream"] = dream
    context.user_data["dating"]["q_index"] = 0
    logger.debug("Переход к тесту: %s", _who(update))
    await _present_question(context, update.effective_chat.id, TEST_QUESTIONS[0])
    return TEST


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    parts = cq.data.split(":")
    if len(parts) != 3:
        return TEST
    _, qid, optid = parts
    data = context.user_data["dating"]
    idx = data["q_index"]
    question = TEST_QUESTIONS[idx]
    if question.id != qid:
        return TEST
    valid = {o.id for o in question.options}
    if optid not in valid:
        return TEST
    data["answers"][qid] = optid
    logger.debug("Ответ %s=%s от %s", qid, optid, _who(update))
    try:
        await cq.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        pass

    nxt = idx + 1
    if nxt >= len(TEST_QUESTIONS):
        return await _finalize(update, context)
    data["q_index"] = nxt
    await _present_question(context, update.effective_chat.id, TEST_QUESTIONS[nxt])
    return TEST


async def _finalize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data.pop("dating", None)
    if data is None:
        return ConversationHandler.END
    profile = Profile(
        user_id=data["user_id"],
        chat_id=data["chat_id"],
        name=data["name"],
        phone=data["phone"],
        username=data.get("username"),
        gender=data["gender"],
        age=data["age"],
        looking_for=data["looking_for"],
        hobbies=data["hobbies"],
        dream=data["dream"],
        photo_file_id=data.get("photo_file_id"),
        answers=data.get("answers", {}),
    )
    save_profile(context.bot_data, profile)
    logger.info("Анкета сохранена: %s", describe_user(profile))
    await context.bot.send_message(chat_id=profile.chat_id, text=texts.profile_saved(profile))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Анкета отменена: %s", _who(update))
    context.user_data.pop("dating", None)
    await update.message.reply_text(
        texts.REGISTRATION_CANCELLED, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_entry, filters=filters.ChatType.PRIVATE)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_name)],
            CONTACT: [
                MessageHandler(filters.CONTACT, on_contact),
                MessageHandler(filters.ALL & ~filters.COMMAND, contact_fallback),
            ],
            GENDER: [CallbackQueryHandler(on_gender, pattern="^gen:")],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_age)],
            LOOKING: [CallbackQueryHandler(on_looking, pattern="^lf:")],
            PHOTO: [
                MessageHandler(filters.PHOTO, on_photo),
                CallbackQueryHandler(on_photo_skip, pattern="^photo_skip$"),
                MessageHandler(filters.ALL & ~filters.COMMAND, photo_fallback),
            ],
            HOBBIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_hobbies)],
            DREAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_dream)],
            TEST: [CallbackQueryHandler(on_answer, pattern="^ans:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="dating_reg",
        persistent=True,
        per_message=False,
    )
