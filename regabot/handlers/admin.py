from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import ADMIN_TABLES, MEETING_IDEAS
from regabot import texts
from regabot.constants import Stage
from regabot.filters import admin_filter, private_filter
from regabot.matching import assign_pairs, badges_with_matches, compute_matches
from regabot.state import TableGame, get_active_table, get_table, set_active_table

logger = logging.getLogger(__name__)

_ADMIN = admin_filter & private_filter


def _admin(update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    return f"admin_uid={user.id if user else None} chat={chat.id if chat else None}"


def _resolve(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[str | None, TableGame | None]:
    user = update.effective_user
    if user is None:
        return None, None
    assigned = ADMIN_TABLES.get(user.id, ())
    tag = get_active_table(context.bot_data, user.id, assigned)
    if tag is None:
        return None, None
    return tag, get_table(context.bot_data, tag)


async def cmd_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("/use от %s", _admin(update))
    assigned = ADMIN_TABLES.get(user.id, ()) if user else ()
    if not context.args:
        active = get_active_table(context.bot_data, user.id, assigned) if user else None
        await update.message.reply_text(texts.use_show(active, ", ".join(assigned)))
        return
    tag = context.args[0].strip().lower()
    if tag not in assigned:
        logger.info("/use отклонён: стол %s не назначен", tag)
        await update.message.reply_text(texts.use_denied(tag, ", ".join(assigned)))
        return
    set_active_table(context.bot_data, user.id, tag)
    logger.info("Активный стол -> %s", tag)
    await update.message.reply_text(texts.use_set(tag))


async def cmd_first(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/first от %s", _admin(update))
    tag, table = _resolve(update, context)
    table.reset_all()
    table.stage = Stage.FIRST
    logger.info("Этап -> FIRST, стол=%s", tag)
    await update.message.reply_text(texts.admin_first_done(tag))


async def cmd_second(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/second от %s", _admin(update))
    tag, table = _resolve(update, context)
    if not table.registrations:
        logger.info("/second отклонён: нет регистраций, стол=%s", tag)
        await update.message.reply_text(texts.ADMIN_NO_REGISTRATIONS)
        return
    table.stage = Stage.SECOND
    await update.message.reply_text(texts.admin_second_done(tag))
    tasks = [(p.chat_id, texts.SECOND_NOTIFY) for p in table.registrations.values()]
    sent, failed = await _broadcast(context, tasks)
    logger.info(
        "/second: стол=%s участников=%d отправлено=%d не_доставлено=%d",
        tag, len(table.registrations), sent, failed,
    )


async def cmd_third(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/third от %s", _admin(update))
    tag, table = _resolve(update, context)
    if not table.registrations:
        logger.info("/third отклонён: нет регистраций, стол=%s", tag)
        await update.message.reply_text(texts.ADMIN_NO_REGISTRATIONS)
        return
    table.stage = Stage.THIRD
    matches = compute_matches(table.registrations, table.sympathies)
    involved = len(badges_with_matches(matches))
    logger.info(
        "/third: стол=%s регистраций=%d метчей=%d участников_с_метчем=%d",
        tag, len(table.registrations), len(matches), involved,
    )
    await update.message.reply_text(texts.admin_report(matches, table.registrations, tag))


async def cmd_love(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/love от %s", _admin(update))
    tag, table = _resolve(update, context)
    if table.love_sent:
        logger.info("/love отклонён: уже отправлено, стол=%s", tag)
        await update.message.reply_text(texts.admin_love_already(tag))
        return
    sent, failed, n_matches, n_pairs = await _send_love(context, tag, table)
    table.love_sent = True
    logger.info(
        "/love: стол=%s mutual=%d paired=%d sent=%d not_delivered=%d",
        tag, n_matches, n_pairs, sent, failed,
    )
    await update.message.reply_text(texts.admin_love_done(sent, failed))


async def cmd_love_force(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/love_force от %s", _admin(update))
    tag, table = _resolve(update, context)
    sent, failed, n_matches, n_pairs = await _send_love(context, tag, table)
    table.love_sent = True
    logger.info(
        "/love_force: стол=%s mutual=%d paired=%d sent=%d not_delivered=%d",
        tag, n_matches, n_pairs, sent, failed,
    )
    await update.message.reply_text(texts.admin_love_done(sent, failed))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/reset от %s", _admin(update))
    tag, table = _resolve(update, context)
    table.reset_all()
    logger.info("Сброс стола=%s этап=NONE", tag)
    await update.message.reply_text(texts.admin_reset_done(tag))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug("/help от %s", _admin(update))
    await update.message.reply_text(texts.ADMIN_HELP)


async def _send_love(
    context: ContextTypes.DEFAULT_TYPE, tag: str, table: TableGame
) -> tuple[int, int, int, int]:
    matches = compute_matches(table.registrations, table.sympathies)
    pairs = assign_pairs(matches)
    regs = table.registrations
    ideas = MEETING_IDEAS.get(tag, [])
    tasks: list[tuple[int, str]] = []
    for m in pairs:
        a = regs[m.a_badge]
        b = regs[m.b_badge]
        tasks.append((a.chat_id, texts.love_message(a, [(m.b_badge, m.super_match)], regs, ideas)))
        tasks.append((b.chat_id, texts.love_message(b, [(m.a_badge, m.super_match)], regs, ideas)))
    sent, failed = await _broadcast(context, tasks)
    return sent, failed, len(matches), len(pairs)


async def _broadcast(
    context: ContextTypes.DEFAULT_TYPE, tasks: list[tuple[int, str]]
) -> tuple[int, int]:
    if not tasks:
        return 0, 0
    coros = [context.bot.send_message(chat_id=cid, text=text) for (cid, text) in tasks]
    results = await asyncio.gather(*coros, return_exceptions=True)
    sent = 0
    failed = 0
    for (cid, _), result in zip(tasks, results, strict=True):
        if isinstance(result, BaseException):
            failed += 1
            logger.warning("Не доставлено chat=%s: %r", cid, result)
        else:
            sent += 1
    return sent, failed


def build_handlers() -> list[CommandHandler]:
    return [
        CommandHandler("use", cmd_use, filters=_ADMIN),
        CommandHandler("first", cmd_first, filters=_ADMIN),
        CommandHandler("second", cmd_second, filters=_ADMIN),
        CommandHandler("third", cmd_third, filters=_ADMIN),
        CommandHandler("love", cmd_love, filters=_ADMIN),
        CommandHandler("love_force", cmd_love_force, filters=_ADMIN),
        CommandHandler("reset", cmd_reset, filters=_ADMIN),
        CommandHandler("help", cmd_help, filters=_ADMIN),
    ]
