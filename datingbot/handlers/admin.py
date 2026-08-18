from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from datingbot import config, texts
from datingbot.constants import Stage
from datingbot.filters import admin_filter, private_filter
from datingbot.keyboards import browse_keyboard
from datingbot.state import (
    all_profiles,
    get_profile,
    likes_of,
    matches_of,
    pop_verify_msgs,
    remove_profile,
    reset_all,
    reset_profiles,
    save_profile,
    set_stage,
)

logger = logging.getLogger(__name__)

_ADMIN = admin_filter & private_filter


def _admin(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"admin_uid={user.id if user else None} chat={chat.id if chat else None}"


def _admin_label(user) -> str:
    handle = f"@{user.username}" if user.username else (user.full_name or "")
    return f"{handle} (uid={user.id})" if handle else f"uid={user.id}"


async def cmd_first(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/first от %s", _admin(update))
    n = reset_profiles(context.bot_data)
    set_stage(context.bot_data, Stage.FIRST)
    logger.info("Этап -> FIRST, сброшено анкет=%d", n)
    await update.message.reply_text(texts.ADMIN_FIRST_DONE, parse_mode=ParseMode.HTML)


async def cmd_dump(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/dump от %s", _admin(update))
    profiles = all_profiles(context.bot_data)
    received: dict[int, int] = {uid: 0 for uid in profiles}
    for uid in profiles:
        for target in likes_of(context.bot_data, uid):
            if target in received:
                received[target] += 1
    matches: set[tuple[int, int]] = set()
    for uid in profiles:
        for other in matches_of(context.bot_data, uid):
            matches.add(tuple(sorted((uid, other))))
    await update.message.reply_text(
        texts.admin_dump(list(profiles.values()), received, sorted(matches)),
        parse_mode=ParseMode.HTML,
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/reset от %s", _admin(update))
    reset_all(context.bot_data)
    logger.info("Сброс: этап=NONE, данные очищены")
    await update.message.reply_text(texts.ADMIN_RESET_DONE, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug("/help от %s", _admin(update))
    await update.message.reply_text(texts.ADMIN_HELP, parse_mode=ParseMode.HTML)


async def on_verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cq = update.callback_query
    user = update.effective_user
    if user is None or user.id not in config.ADMIN_USER_IDS:
        await cq.answer("Недостаточно прав", show_alert=True)
        return
    try:
        _, action, raw_uid = cq.data.split(":", 2)
        target_id = int(raw_uid)
    except (AttributeError, ValueError):
        return
    if action not in ("ok", "no"):
        return

    profile = get_profile(context.bot_data, target_id)
    if profile is None or profile.verified:
        await cq.answer(texts.VERIFY_ALREADY_DONE, show_alert=True)
        return
    await cq.answer()

    admin_label = _admin_label(user)
    approved = action == "ok"
    refs = pop_verify_msgs(context.bot_data, target_id)
    if approved:
        profile.verified = True
        profile.verified_by = admin_label
        save_profile(context.bot_data, profile)
    else:
        remove_profile(context.bot_data, target_id)
    logger.info(
        "Верификация uid=%s: %s (%s)",
        target_id,
        "одобрена" if approved else "отклонена",
        admin_label,
    )

    await _update_admin_cards(
        context, refs, texts.admin_verdict_card(profile, approved, admin_label)
    )
    try:
        if approved:
            await context.bot.send_message(
                chat_id=profile.chat_id,
                text=texts.VERIFICATION_APPROVED,
                parse_mode=ParseMode.HTML,
                reply_markup=browse_keyboard(),
            )
        else:
            await context.bot.send_message(
                chat_id=profile.chat_id,
                text=texts.VERIFICATION_REJECTED,
                parse_mode=ParseMode.HTML,
            )
    except BaseException as exc:  # noqa: BLE001
        logger.warning("Не доставлено решение верификации uid=%s: %r", target_id, exc)


async def _update_admin_cards(
    context: ContextTypes.DEFAULT_TYPE,
    refs: list[tuple[int, int]],
    text: str,
) -> None:
    """Заменяет карточки верификации у всех админов на вердикт (кто решил)."""
    for chat_id, message_id in refs:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
            continue
        except BadRequest:
            pass
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            logger.warning(
                "Не удалось обновить карточку верификации chat=%s msg=%s",
                chat_id,
                message_id,
            )


def build_handlers() -> list[CommandHandler | CallbackQueryHandler]:
    return [
        CommandHandler("first", cmd_first, filters=_ADMIN),
        CommandHandler("dump", cmd_dump, filters=_ADMIN),
        CommandHandler("reset", cmd_reset, filters=_ADMIN),
        CommandHandler("help", cmd_help, filters=_ADMIN),
        CallbackQueryHandler(on_verify_button, pattern="^verify:"),
    ]
