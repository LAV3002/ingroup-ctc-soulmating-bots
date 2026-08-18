from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from datingbot import texts
from datingbot.keyboards import browse_keyboard, match_keyboard, refresh_keyboard, swipe_keyboard
from datingbot.logging_setup import describe_user
from datingbot.matching import candidates_for
from datingbot.models import Profile
from datingbot.state import (
    LIKE,
    PASS,
    all_profiles,
    get_profile,
    likes_of,
    record_match,
    record_swipe,
    refresh_username,
    save_profile,
    viewed_ids,
)

logger = logging.getLogger(__name__)

VIEWING = 0

TARGET_KEY = "browse_target"


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"uid={user.id if user else None} chat={chat.id if chat else None}"


def _current_profile(
    context: ContextTypes.DEFAULT_TYPE, update: Update
) -> Profile | None:
    """Анкета пользователя с обновлённым @username (они меняются со временем)."""
    user = update.effective_user
    if user is None:
        return None
    profile = get_profile(context.bot_data, user.id)
    if profile is None:
        return None
    if refresh_username(profile, user.username):
        save_profile(context.bot_data, profile)
    return profile


def _pick_candidate(bot_data: dict, profile: Profile) -> Profile | None:
    candidates = candidates_for(
        profile, all_profiles(bot_data), viewed_ids(bot_data, profile.user_id)
    )
    return candidates[0] if candidates else None


async def _send_card(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, profile: Profile
) -> None:
    caption = texts.swipe_card(profile)
    if profile.photo_file_id:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=profile.photo_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=swipe_keyboard(),
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=swipe_keyboard(),
        )


async def _show_next(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    profile: Profile,
    message_id: int | None = None,
) -> int:
    """Убирает кнопки с текущей карточки и показывает следующую (или «конец»)."""
    if message_id is not None:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id, message_id=message_id
            )
        except BadRequest:
            pass

    candidate = _pick_candidate(context.bot_data, profile)
    if candidate is None:
        context.user_data.pop(TARGET_KEY, None)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.BROWSE_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=refresh_keyboard(),
        )
        return ConversationHandler.END

    context.user_data[TARGET_KEY] = candidate.user_id
    await _send_card(context, update.effective_chat.id, candidate)
    return VIEWING


async def browse_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("/browse от %s", _who(update))
    profile = _current_profile(context, update)
    if profile is None:
        await update.message.reply_text(
            texts.START_CLOSED, parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    if not profile.verified:
        await update.message.reply_text(
            texts.PROFILE_PENDING, parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    return await _show_next(context, update, profile)


async def on_browse_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    profile = _current_profile(context, update)
    if profile is None:
        await cq.edit_message_text(texts.START_CLOSED, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    if not profile.verified:
        await cq.edit_message_text(texts.PROFILE_PENDING, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    return await _show_next(context, update, profile, message_id=cq.message.message_id)


async def on_swipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cq = update.callback_query
    await cq.answer()
    action = cq.data.split(":", 1)[1]
    message_id = cq.message.message_id if cq.message else None

    if action == "stop":
        context.user_data.pop(TARGET_KEY, None)
        if cq.message is not None:
            try:
                await cq.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.BROWSE_STOPPED,
            parse_mode=ParseMode.HTML,
            reply_markup=browse_keyboard(),
        )
        return ConversationHandler.END

    if action not in (LIKE, PASS):
        return VIEWING

    profile = _current_profile(context, update)
    target_id = context.user_data.get(TARGET_KEY)
    if profile is None:
        return ConversationHandler.END
    if target_id is None:
        return await _show_next(context, update, profile, message_id)

    record_swipe(context.bot_data, profile.user_id, target_id, action)
    context.user_data.pop(TARGET_KEY, None)
    logger.debug("Свайп uid=%s -> uid=%s: %s", profile.user_id, target_id, action)

    if action == LIKE and profile.user_id in likes_of(context.bot_data, target_id):
        await _notify_match(context, update, profile.user_id, target_id)

    return await _show_next(context, update, profile, message_id)


async def _notify_match(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    a_uid: int,
    b_uid: int,
) -> None:
    a = get_profile(context.bot_data, a_uid)
    b = get_profile(context.bot_data, b_uid)
    if a is None or b is None:
        return
    record_match(context.bot_data, a_uid, b_uid)
    logger.info("Метч: uid=%s + uid=%s", *sorted((a_uid, b_uid)))
    for who, partner in ((a, b), (b, a)):
        card = texts.match_message(partner)
        markup = match_keyboard(partner.username)
        try:
            if partner.photo_file_id:
                await context.bot.send_photo(
                    chat_id=who.chat_id,
                    photo=partner.photo_file_id,
                    caption=card,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
            else:
                await context.bot.send_message(
                    chat_id=who.chat_id,
                    text=card,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
        except BaseException as exc:  # noqa: BLE001
            logger.warning("Не доставлено сообщение о метче %s: %r", describe_user(who), exc)


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler(
                "browse", browse_entry, filters=filters.ChatType.PRIVATE
            ),
            CallbackQueryHandler(on_browse_button, pattern="^browse:start$"),
        ],
        states={
            VIEWING: [CallbackQueryHandler(on_swipe, pattern="^swipe:")],
        },
        fallbacks=[],
        name="dating_browse",
        persistent=True,
        per_message=False,
    )
