from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from datingbot import texts
from datingbot.constants import Stage
from datingbot.filters import admin_filter, private_filter
from datingbot.matching import assign_pairs
from datingbot.models import Profile
from datingbot.state import all_profiles, reset_all, reset_profiles, set_stage

logger = logging.getLogger(__name__)

_ADMIN = admin_filter & private_filter


def _admin(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"admin_uid={user.id if user else None} chat={chat.id if chat else None}"


async def cmd_first(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/first от %s", _admin(update))
    n = reset_profiles(context.bot_data)
    set_stage(context.bot_data, Stage.FIRST)
    logger.info("Этап -> FIRST, сброшено анкет=%d", n)
    await update.message.reply_text(texts.ADMIN_FIRST_DONE)


async def cmd_second(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/second от %s", _admin(update))
    profiles = all_profiles(context.bot_data)
    if len(profiles) < 2:
        logger.info("/second отклонён: анкет=%d", len(profiles))
        await update.message.reply_text(texts.ADMIN_NOT_ENOUGH)
        return

    pairs = assign_pairs(profiles)
    matched: set[int] = {uid for m in pairs for uid in (m.a_uid, m.b_uid)}
    logger.info(
        "/second: анкет=%d пар=%d участников_с_метчем=%d",
        len(profiles), len(pairs), len(matched),
    )

    tasks: list[tuple[int, Profile | None]] = []
    for m in pairs:
        a = profiles[m.a_uid]
        b = profiles[m.b_uid]
        tasks.append((a.chat_id, b))
        tasks.append((b.chat_id, a))
    for uid, p in profiles.items():
        if uid not in matched:
            tasks.append((p.chat_id, None))

    sent, failed = await _deliver(context, tasks)
    set_stage(context.bot_data, Stage.SECOND)
    await update.message.reply_text(texts.admin_second_done(sent, failed, len(pairs)))


async def cmd_dump(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/dump от %s", _admin(update))
    profiles = all_profiles(context.bot_data)
    pairs = assign_pairs(profiles) if len(profiles) >= 2 else []
    await update.message.reply_text(texts.admin_dump(list(profiles.values()), pairs))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/reset от %s", _admin(update))
    reset_all(context.bot_data)
    logger.info("Сброс: этап=NONE, анкеты очищены")
    await update.message.reply_text(texts.ADMIN_RESET_DONE)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug("/help от %s", _admin(update))
    await update.message.reply_text(texts.ADMIN_HELP)


async def _deliver(
    context: ContextTypes.DEFAULT_TYPE, tasks: list[tuple[int, Profile | None]]
) -> tuple[int, int]:
    if not tasks:
        return 0, 0

    async def one(chat_id: int, partner: Profile | None) -> bool:
        try:
            if partner is None:
                await context.bot.send_message(chat_id=chat_id, text=texts.no_match_message())
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text=texts.match_intro(partner)
                )
                if partner.photo_file_id:
                    await context.bot.send_photo(chat_id=chat_id, photo=partner.photo_file_id)
            return True
        except BaseException as exc:  # noqa: BLE001
            logger.warning("Не доставлено chat=%s: %r", chat_id, exc)
            return False

    results = await asyncio.gather(*(one(c, p) for (c, p) in tasks))
    sent = sum(1 for r in results if r)
    failed = len(results) - sent
    return sent, failed


def build_handlers() -> list[CommandHandler]:
    return [
        CommandHandler("first", cmd_first, filters=_ADMIN),
        CommandHandler("second", cmd_second, filters=_ADMIN),
        CommandHandler("dump", cmd_dump, filters=_ADMIN),
        CommandHandler("reset", cmd_reset, filters=_ADMIN),
        CommandHandler("help", cmd_help, filters=_ADMIN),
    ]
