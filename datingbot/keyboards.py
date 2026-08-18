from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF


def gender_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("♂ Мужчина", callback_data=f"gen:{GENDER_M}"),
            InlineKeyboardButton("♀ Женщина", callback_data=f"gen:{GENDER_F}"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def looking_for_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("👨 Парней", callback_data=f"lf:{LOOKING_M}"),
            InlineKeyboardButton("👩 Девушек", callback_data=f"lf:{LOOKING_F}"),
            InlineKeyboardButton("✨ Всех", callback_data=f"lf:{LOOKING_MF}"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def swipe_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("💔 Мимо", callback_data="swipe:pass"),
            InlineKeyboardButton("❤️ Нравится", callback_data="swipe:like"),
        ],
        [InlineKeyboardButton("⏹ Стоп", callback_data="swipe:stop")],
    ]
    return InlineKeyboardMarkup(rows)


def browse_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("▶️ Смотреть анкеты", callback_data="browse:start")]]
    )


def refresh_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Обновить", callback_data="browse:start")]]
    )


def match_keyboard(username: str | None) -> InlineKeyboardMarkup | None:
    if not username:
        return None
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"💬 Написать @{username}", url=f"https://t.me/{username}"
                )
            ]
        ]
    )


def verification_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"verify:ok:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"verify:no:{user_id}"),
        ]
    ]
    return InlineKeyboardMarkup(rows)
