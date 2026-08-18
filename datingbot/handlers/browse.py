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
from datingbot.keyboards import (
    browse_keyboard,
    match_keyboard,
    refresh_keyboard,
    swipe_keyboard,
)
from datingbot.logging_setup import describe_user
from datingbot.matching import candidates_for
from datingbot.models import Profile
from datingbot.state import (
    LIKE,
    PASS,
    all_profiles,
    get_profile,
    likes_of,
    matches_of,
    record_match,
    record_swipe,
    refresh_username,
    save_profile,
    viewed_ids,
)

logger = logging.getLogger(__name__)

VIEWING = 0


def _who(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"uid={user.id if user else None} chat={chat.id if chat else None}"


def _current_profile(context: ContextTypes.DEFAULT_TYPE, update: Update) -> Profile | None:
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


async def _send_card(context: ContextTypes.DEFAULT_TYPE, chat_id: int, profile: Profile) -> None:
    caption = texts.swipe_card(profile)
    markup = swipe_keyboard(profile.user_id)
    if profile.photo_file_id:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=profile.photo_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )


async def _show_next(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    profile: Profile,
    message_id: int | None = None,
) -> int:
    if message_id is not None:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id, message_id=message_id
            )
        except BadRequest:
            pass

    candidate = _pick_candidate(context.bot_data, profile)
    if candidate is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.BROWSE_EMPTY,
            parse_mode=ParseMode.HTML,
            reply_markup=refresh_keyboard(),
        )
        return ConversationHandler.END

    await _send_card(context, update.effective_chat.id, candidate)
    return VIEWING


async def browse_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("/browse от %s", _who(update))
    profile = _current_profile(context, update)
    if profile is None:
        await update.message.reply_text(texts.PROFILE_REQUIRED, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    if not profile.verified:
        await update.message.reply_text(texts.PROFILE_PENDING, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    return await _show_next(context, update, profile)


async def on_browse_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    profile = _current_profile(context, update)
    if profile is None or not profile.verified:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.PROFILE_REQUIRED if profile is None else texts.PROFILE_PENDING,
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    return await _show_next(context, update, profile, message_id=query.message.message_id)


async def on_swipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) >= 2 else ""
    message_id = query.message.message_id if query.message else None

    if action == "stop":
        await query.answer(texts.SWIPE_STOPPED_TOAST)
        if query.message is not None:
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts.BROWSE_STOPPED,
            parse_mode=ParseMode.HTML,
            reply_markup=browse_keyboard(),
        )
        return ConversationHandler.END

    if action not in (LIKE, PASS) or len(parts) != 3:
        await query.answer()
        return VIEWING
    try:
        target_id = int(parts[2])
    except ValueError:
        await query.answer()
        return VIEWING

    await query.answer(texts.SWIPE_LIKED if action == LIKE else texts.SWIPE_PASSED)
    profile = _current_profile(context, update)
    if profile is None:
        return ConversationHandler.END

    already_viewed = target_id in viewed_ids(context.bot_data, profile.user_id)
    if already_viewed:
        if message_id is not None:
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                pass
        return VIEWING

    record_swipe(context.bot_data, profile.user_id, target_id, action)
    logger.debug("Свайп uid=%s -> uid=%s: %s", profile.user_id, target_id, action)

    is_mutual = profile.user_id in likes_of(context.bot_data, target_id)
    already_matched = target_id in matches_of(context.bot_data, profile.user_id)
    if action == LIKE and is_mutual and not already_matched:
        await _notify_match(context, profile.user_id, target_id)

    return await _show_next(context, update, profile, message_id)


async def _notify_match(
    context: ContextTypes.DEFAULT_TYPE,
    a_uid: int,
    b_uid: int,
) -> None:
    first = get_profile(context.bot_data, a_uid)
    second = get_profile(context.bot_data, b_uid)
    if first is None or second is None:
        return
    record_match(context.bot_data, a_uid, b_uid)
    logger.info("Метч: uid=%s + uid=%s", *sorted((a_uid, b_uid)))
    for recipient, partner in ((first, second), (second, first)):
        card = texts.match_message(partner)
        markup = match_keyboard(partner.username)
        try:
            if partner.photo_file_id:
                await context.bot.send_photo(
                    chat_id=recipient.chat_id,
                    photo=partner.photo_file_id,
                    caption=card,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
            else:
                await context.bot.send_message(
                    chat_id=recipient.chat_id,
                    text=card,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
        except BaseException as exc:  # noqa: BLE001
            logger.warning(
                "Не доставлено сообщение о метче %s: %r",
                describe_user(recipient),
                exc,
            )


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("browse", browse_entry, filters=filters.ChatType.PRIVATE),
            CallbackQueryHandler(on_browse_button, pattern="^browse:start$"),
        ],
        states={
            VIEWING: [
                CallbackQueryHandler(on_swipe, pattern=r"^swipe:(?:pass:\d+|like:\d+|stop)$")
            ],
        },
        fallbacks=[],
        name="dating_browse",
        persistent=True,
        per_message=False,
        allow_reentry=True,
    )
