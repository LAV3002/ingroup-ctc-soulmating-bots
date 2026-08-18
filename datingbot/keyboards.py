from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF


def _navigation_row(back_to: str | None = None) -> list[InlineKeyboardButton]:
    row: list[InlineKeyboardButton] = []
    if back_to:
        row.append(InlineKeyboardButton("← НАЗАД", callback_data=f"reg:back:{back_to}"))
    row.append(InlineKeyboardButton("ОТМЕНИТЬ ×", callback_data="reg:cancel"))
    return row


def registration_nav_keyboard(back_to: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([_navigation_row(back_to)])


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("МУЖЧИНА", callback_data=f"gen:{GENDER_M}"),
                InlineKeyboardButton("ЖЕНЩИНА", callback_data=f"gen:{GENDER_F}"),
            ],
            _navigation_row("name"),
        ]
    )


def looking_for_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("МУЖЧИН", callback_data=f"lf:{LOOKING_M}"),
                InlineKeyboardButton("ЖЕНЩИН", callback_data=f"lf:{LOOKING_F}"),
            ],
            [InlineKeyboardButton("ВСЕХ", callback_data=f"lf:{LOOKING_MF}")],
            _navigation_row("age"),
        ]
    )


def swipe_keyboard(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("×  ДАЛЬШЕ", callback_data=f"swipe:pass:{target_id}"),
                InlineKeyboardButton("♥  НРАВИТСЯ", callback_data=f"swipe:like:{target_id}"),
            ],
            [InlineKeyboardButton("ПАУЗА", callback_data="swipe:stop")],
        ]
    )


def browse_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("СМОТРЕТЬ АНКЕТЫ →", callback_data="browse:start")]]
    )


def refresh_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("ПРОВЕРИТЬ ЕЩЁ РАЗ", callback_data="browse:start")]]
    )


def profile_keyboard(verified: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if verified:
        rows.append([InlineKeyboardButton("СМОТРЕТЬ АНКЕТЫ →", callback_data="browse:start")])
    rows.append([InlineKeyboardButton("ИЗМЕНИТЬ АНКЕТУ", callback_data="profile:edit")])
    return InlineKeyboardMarkup(rows)


def match_keyboard(username: str | None) -> InlineKeyboardMarkup | None:
    if not username:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"НАПИСАТЬ @{username} →", url=f"https://t.me/{username}")]]
    )


def verification_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ОДОБРИТЬ", callback_data=f"verify:ok:{user_id}"),
                InlineKeyboardButton("ОТКЛОНИТЬ", callback_data=f"verify:no:{user_id}"),
            ]
        ]
    )
