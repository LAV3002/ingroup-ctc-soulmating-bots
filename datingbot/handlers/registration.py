from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from datingbot import config, texts
from datingbot.constants import (
    GENDERS,
    LOOKING_FOR,
    NAME_MAX_LENGTH,
    PROFILE_TEXT_MAX_LENGTH,
    Stage,
)
from datingbot.keyboards import (
    gender_keyboard,
    looking_for_keyboard,
    profile_keyboard,
    registration_nav_keyboard,
    verification_keyboard,
)
from datingbot.logging_setup import describe_user
from datingbot.models import Profile
from datingbot.state import (
    get_profile,
    get_stage,
    pop_verify_msgs,
    remember_verify_msg,
    remove_profile,
    save_profile,
)

logger = logging.getLogger(__name__)

NAME, GENDER, AGE, LOOKING, PHOTO, HOBBIES, DREAM = range(7)
ONBOARDING_ART = Path(__file__).resolve().parent.parent / "assets" / "soulmating-onboarding.png"


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"uid={user.id if user else None} chat={chat.id if chat else None}"


def _new_draft(update: Update, *, editing: bool = False) -> dict:
    user = update.effective_user
    return {
        "user_id": user.id if user else 0,
        "chat_id": update.effective_chat.id,
        "username": user.username if user else None,
        "photo_file_id": None,
        "editing": editing,
    }


async def _send_intro(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
) -> None:
    markup = registration_nav_keyboard()
    try:
        with ONBOARDING_ART.open("rb") as artwork:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=artwork,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
    except (OSError, TelegramError) as exc:
        logger.warning("Не удалось отправить стартовый арт: %r", exc)
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )


async def _send_profile_overview(
    context: ContextTypes.DEFAULT_TYPE,
    profile: Profile,
) -> None:
    caption = texts.profile_overview(profile)
    markup = profile_keyboard(profile.verified)
    if profile.photo_file_id:
        await context.bot.send_photo(
            chat_id=profile.chat_id,
            photo=profile.photo_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=profile.chat_id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )


async def _begin_form(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    editing: bool = False,
) -> int:
    context.user_data["dating"] = _new_draft(update, editing=editing)
    logger.info("%s анкеты: %s", "Редактирование" if editing else "Начало", _who(update))
    caption = texts.profile_edit_intro() if editing else texts.start_open(False)
    await _send_intro(context, update.effective_chat.id, caption)
    return NAME


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("/start от %s", _who(update))
    if get_stage(context.bot_data) != Stage.FIRST:
        await update.message.reply_text(texts.START_CLOSED, parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    user = update.effective_user
    existing = get_profile(context.bot_data, user.id) if user else None
    if existing is not None:
        await _send_profile_overview(context, existing)
        return ConversationHandler.END
    return await _begin_form(update, context)


async def profile_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    existing = get_profile(context.bot_data, user.id) if user else None
    if existing is not None:
        await _send_profile_overview(context, existing)
        return ConversationHandler.END
    if get_stage(context.bot_data) != Stage.FIRST:
        await update.message.reply_text(texts.START_CLOSED, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    return await _begin_form(update, context)


async def edit_profile_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if get_stage(context.bot_data) != Stage.FIRST:
        await query.answer("Сейчас анкеты закрыты", show_alert=True)
        return ConversationHandler.END
    user = update.effective_user
    if user is None or get_profile(context.bot_data, user.id) is None:
        await query.answer("Анкета не найдена", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    return await _begin_form(update, context, editing=True)


async def on_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text(
            texts.NAME_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard(),
        )
        return NAME
    if len(name) > NAME_MAX_LENGTH:
        await update.message.reply_text(
            texts.NAME_TOO_LONG.format(max=NAME_MAX_LENGTH),
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard(),
        )
        return NAME
    context.user_data["dating"]["name"] = name
    await update.message.reply_text(
        texts.ASK_GENDER,
        parse_mode=ParseMode.HTML,
        reply_markup=gender_keyboard(),
    )
    return GENDER


async def on_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    value = query.data.split(":", 1)[1]
    if value not in GENDERS:
        return GENDER
    context.user_data["dating"]["gender"] = value
    await query.edit_message_text(
        texts.ASK_AGE,
        parse_mode=ParseMode.HTML,
        reply_markup=registration_nav_keyboard("gender"),
    )
    return AGE


async def on_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    try:
        age = int(raw)
    except ValueError:
        await update.message.reply_text(
            texts.AGE_INVALID,
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("gender"),
        )
        return AGE
    if age < config.MIN_AGE or age > config.MAX_AGE:
        await update.message.reply_text(
            texts.AGE_OUT_OF_RANGE.format(min=config.MIN_AGE, max=config.MAX_AGE),
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("gender"),
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
    query = update.callback_query
    await query.answer()
    value = query.data.split(":", 1)[1]
    if value not in LOOKING_FOR:
        return LOOKING
    context.user_data["dating"]["looking_for"] = value
    await query.edit_message_text(
        texts.ASK_PHOTO,
        parse_mode=ParseMode.HTML,
        reply_markup=registration_nav_keyboard("looking"),
    )
    return PHOTO


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photos = update.message.photo
    if not photos:
        await update.message.reply_text(
            texts.PHOTO_INVALID,
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("looking"),
        )
        return PHOTO
    context.user_data["dating"]["photo_file_id"] = photos[-1].file_id
    logger.debug("Фото получено от %s", _who(update))
    await update.message.reply_text(
        f"{texts.PHOTO_SAVED_ACK}\n\n{texts.ASK_HOBBIES.format(max=PROFILE_TEXT_MAX_LENGTH)}",
        parse_mode=ParseMode.HTML,
        reply_markup=registration_nav_keyboard("photo"),
    )
    return HOBBIES


async def photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        texts.PHOTO_INVALID,
        parse_mode=ParseMode.HTML,
        reply_markup=registration_nav_keyboard("looking"),
    )
    return PHOTO


async def on_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hobbies = (update.message.text or "").strip()
    if not hobbies:
        await update.message.reply_text(
            texts.TEXT_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("photo"),
        )
        return HOBBIES
    if len(hobbies) > PROFILE_TEXT_MAX_LENGTH:
        await update.message.reply_text(
            texts.TEXT_TOO_LONG.format(max=PROFILE_TEXT_MAX_LENGTH),
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("photo"),
        )
        return HOBBIES
    context.user_data["dating"]["hobbies"] = hobbies
    await update.message.reply_text(
        texts.ASK_DREAM.format(max=PROFILE_TEXT_MAX_LENGTH),
        parse_mode=ParseMode.HTML,
        reply_markup=registration_nav_keyboard("hobbies"),
    )
    return DREAM


async def on_dream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dream = (update.message.text or "").strip()
    if not dream:
        await update.message.reply_text(
            texts.TEXT_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("hobbies"),
        )
        return DREAM
    if len(dream) > PROFILE_TEXT_MAX_LENGTH:
        await update.message.reply_text(
            texts.TEXT_TOO_LONG.format(max=PROFILE_TEXT_MAX_LENGTH),
            parse_mode=ParseMode.HTML,
            reply_markup=registration_nav_keyboard("hobbies"),
        )
        return DREAM
    context.user_data["dating"]["dream"] = dream
    await _finalize(update, context)
    return ConversationHandler.END


async def _retire_old_verification_cards(
    context: ContextTypes.DEFAULT_TYPE,
    refs: list[tuple[int, int]],
) -> None:
    for chat_id, message_id in refs:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
            )
        except TelegramError as exc:
            logger.warning("Не удалось закрыть старую карточку модерации: %r", exc)


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

    old_refs = pop_verify_msgs(context.bot_data, profile.user_id)
    remove_profile(context.bot_data, profile.user_id)
    save_profile(context.bot_data, profile)
    await _retire_old_verification_cards(context, old_refs)
    logger.info("Анкета сохранена: %s", describe_user(profile))

    if profile.photo_file_id:
        await context.bot.send_photo(
            chat_id=profile.chat_id,
            photo=profile.photo_file_id,
            caption=texts.profile_saved(profile),
            parse_mode=ParseMode.HTML,
        )
    else:
        await context.bot.send_message(
            chat_id=profile.chat_id,
            text=texts.profile_saved(profile),
            parse_mode=ParseMode.HTML,
        )
    await _send_admin_verification(context, profile)


async def _send_admin_verification(context: ContextTypes.DEFAULT_TYPE, profile: Profile) -> None:
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
    await update.message.reply_text(texts.REGISTRATION_CANCELLED, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def on_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    action = query.data.split(":")
    await query.answer()

    if len(action) >= 2 and action[1] == "cancel":
        context.user_data.pop("dating", None)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.REGISTRATION_CANCELLED,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if len(action) != 3 or action[1] != "back":
        return ConversationHandler.END

    target = action[2]
    prompts: dict[str, tuple[int, str, InlineKeyboardMarkup]] = {
        "name": (NAME, texts.ASK_NAME, registration_nav_keyboard()),
        "gender": (GENDER, texts.ASK_GENDER, gender_keyboard()),
        "age": (
            AGE,
            texts.ASK_AGE,
            registration_nav_keyboard("gender"),
        ),
        "looking": (LOOKING, texts.ASK_LOOKING_FOR, looking_for_keyboard()),
        "photo": (
            PHOTO,
            texts.ASK_PHOTO,
            registration_nav_keyboard("looking"),
        ),
        "hobbies": (
            HOBBIES,
            texts.ASK_HOBBIES.format(max=PROFILE_TEXT_MAX_LENGTH),
            registration_nav_keyboard("photo"),
        ),
    }
    destination = prompts.get(target)
    if destination is None:
        return ConversationHandler.END
    state, prompt, markup = destination
    await query.edit_message_text(
        prompt,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )
    return state


def _navigation_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(on_navigation, pattern="^reg:")


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_entry, filters=filters.ChatType.PRIVATE),
            CommandHandler("profile", profile_entry, filters=filters.ChatType.PRIVATE),
            CallbackQueryHandler(edit_profile_entry, pattern="^profile:edit$"),
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_name),
                _navigation_handler(),
            ],
            GENDER: [
                CallbackQueryHandler(on_gender, pattern="^gen:"),
                _navigation_handler(),
            ],
            AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_age),
                _navigation_handler(),
            ],
            LOOKING: [
                CallbackQueryHandler(on_looking, pattern="^lf:"),
                _navigation_handler(),
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, on_photo),
                _navigation_handler(),
                MessageHandler(filters.ALL & ~filters.COMMAND, photo_fallback),
            ],
            HOBBIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_hobbies),
                _navigation_handler(),
            ],
            DREAM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_dream),
                _navigation_handler(),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="dating_reg",
        persistent=True,
        per_message=False,
        allow_reentry=True,
    )
