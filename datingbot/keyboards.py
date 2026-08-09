from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.questions import Question


def contact_keyboard() -> ReplyKeyboardMarkup:
    button = KeyboardButton(text="Поделиться контактом", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def gender_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("♂ М", callback_data=f"gen:{GENDER_M}"),
            InlineKeyboardButton("♀ Ж", callback_data=f"gen:{GENDER_F}"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def looking_for_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Мужчин", callback_data=f"lf:{LOOKING_M}"),
            InlineKeyboardButton("Женщин", callback_data=f"lf:{LOOKING_F}"),
            InlineKeyboardButton("М/Ж", callback_data=f"lf:{LOOKING_MF}"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


def question_keyboard(question: Question) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(opt.text, callback_data=f"ans:{question.id}:{opt.id}")]
        for opt in question.options
    ]
    return InlineKeyboardMarkup(rows)


def photo_choice_keyboard(question: Question) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(str(i + 1), callback_data=f"ans:{question.id}:{opt.id}")
            for i, opt in enumerate(question.options)
        ]
    ]
    return InlineKeyboardMarkup(rows)


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Пропустить фото", callback_data="photo_skip")]]
    )
