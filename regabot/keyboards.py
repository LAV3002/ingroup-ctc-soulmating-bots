from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def contact_keyboard() -> ReplyKeyboardMarkup:
    button = KeyboardButton(text="Поделиться контактом", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)


def table_keyboard(open_tags: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(tag, callback_data=f"tbl:{tag}")] for tag in open_tags]
    return InlineKeyboardMarkup(rows)


def use_table_keyboard(
    assigned: tuple[str, ...] | list[str], active: str | None = None
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                (f"\u2705 {tag}" if tag == active else tag),
                callback_data=f"use:{tag}",
            )
        ]
        for tag in assigned
    ]
    return InlineKeyboardMarkup(rows)


def sympathy_table_keyboard(tags: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(tag, callback_data=f"sym:{tag}")] for tag in tags]
    return InlineKeyboardMarkup(rows)


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
