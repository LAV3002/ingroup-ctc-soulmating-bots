from __future__ import annotations

import html

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.models import Profile


def _esc(value: str) -> str:
    """Экранирование пользовательского ввода для HTML parse mode."""
    return html.escape(value, quote=False)


def _gender_label(g: str) -> str:
    return "М" if g == GENDER_M else "Ж" if g == GENDER_F else g


def _looking_label(lf: str) -> str:
    return {LOOKING_M: "М", LOOKING_F: "Ж", LOOKING_MF: "М/Ж"}.get(lf, lf)


def _gender_emoji(g: str) -> str:
    return "👨" if g == GENDER_M else "👩" if g == GENDER_F else g


def _looking_emoji(lf: str) -> str:
    return {LOOKING_M: "👨", LOOKING_F: "👩", LOOKING_MF: "👨👩"}.get(lf, lf)


def _card_header(p: Profile) -> str:
    return (
        f"{_gender_emoji(p.gender)} <b>{_esc(p.name)}, {p.age}</b> · "
        f"ищет {_looking_emoji(p.looking_for)}"
    )


def _card_body(p: Profile, contact: bool = False) -> str:
    lines = [
        _card_header(p),
        "",
        f"🎯 <b>Хобби:</b> {_esc(p.hobbies)}",
        f"✨ <b>Мечта:</b> {_esc(p.dream)}",
    ]
    if contact:
        lines.extend(["", _contact_line(p)])
    return "\n".join(lines)


def _contact_line(p: Profile) -> str:
    if p.username:
        return f"💬 Telegram: @{_esc(p.username)} (https://t.me/{_esc(p.username)})"
    return "⚠️ @username не указан — обратись к организаторам"


# --- /start / регистрация ---
START_CLOSED = (
    "🔒 <b>Регистрация закрыта</b>\n\n"
    "Привет! Я бот-знакомства SoulMating Dating.\n"
    "Сейчас регистрация закрыта — дождись начала ивента."
)


def start_open(has_profile: bool) -> str:
    if has_profile:
        return (
            "💫 <b>С возвращением!</b>\n\n"
            "Твоя анкета уже заполнена и проверена.\n"
            "Смотреть анкеты можно командой /browse или кнопкой ниже."
        )
    return (
        "💘 <b>Привет! Я бот-знакомств SoulMating Dating.</b>\n\n"
        "Заполним анкету — это займёт пару минут.\n\n"
        "<b>Шаг 1/7</b> · Как тебя зовут? (введи имя текстом)"
    )


NAME_EMPTY = "✏️ Пожалуйста, введи имя текстом."
ASK_GENDER = "<b>Шаг 2/7</b> · Укажи свой пол:"
ASK_AGE = "<b>Шаг 3/7</b> · Укажи свой возраст (целое число):"
AGE_INVALID = "⚠️ Возраст должен быть целым числом. Попробуй ещё раз."
AGE_OUT_OF_RANGE = "⚠️ Возраст должен быть от {min} до {max}. Попробуй ещё раз."
ASK_LOOKING_FOR = "<b>Шаг 4/7</b> · Кого ты ищешь?"
ASK_PHOTO = "<b>Шаг 5/7</b> · Прикрепи своё фото (обязательно):"
PHOTO_INVALID = "📷 Фото обязательно. Пожалуйста, отправь фото."
PHOTO_SAVED_ACK = "📸 Фото сохранено!"
ASK_HOBBIES = "<b>Шаг 6/7</b> · Расскажи о своих хобби (свободным текстом):"
ASK_DREAM = "<b>Шаг 7/7</b> · Какая твоя главная мечта в жизни? (свободным текстом):"
TEXT_EMPTY = "✍️ Пожалуйста, введи ответ текстом."
REGISTRATION_CANCELLED = (
    "😔 <b>Анкета отменена.</b>\nМожно начать заново командой /start."
)


def profile_saved(p: Profile) -> str:
    return (
        "✅ <b>Анкета сохранена! Спасибо.</b>\n\n"
        f"{_card_body(p)}\n\n"
        "🕐 Анкета отправлена на проверку администраторам.\n"
        "Как только её одобрят, пришлём уведомление — и можно смотреть анкеты."
    )


PROFILE_PENDING = (
    "🕐 <b>Твоя анкета ещё на проверке</b>\n\n"
    "Как только её одобрят, пришлём уведомление — и можно смотреть анкеты."
)
VERIFICATION_APPROVED = (
    "🎉 <b>Твою анкету одобрили!</b>\n\n"
    "Теперь можно смотреть анкеты: жми кнопку ниже или /browse."
)
VERIFICATION_REJECTED = (
    "💔 <b>К сожалению, твою анкету не одобрили.</b>\n\n"
    "Можно заполнить её заново командой /start."
)


# --- Свайпы ---
def swipe_card(p: Profile) -> str:
    return _card_body(p)


BROWSE_EMPTY = (
    "📭 <b>Ты просмотрел все доступные анкеты</b>\n\n"
    "Новые участники появляются в течение ивента — "
    "жми «Обновить» или зайди позже (/browse)."
)
BROWSE_STOPPED = (
    "⏹ <b>Просмотр остановлен.</b>\nВозвращайся кнопкой ниже или командой /browse."
)


# --- Метчи ---
def match_message(partner: Profile) -> str:
    return "🎉 <b>Это взаимно! У вас метч!</b>\n\n" + _card_body(partner, contact=True)


# --- Админка ---
ADMIN_FIRST_DONE = (
    "✅ <b>Этап 1 открыт</b>\n\n"
    "Участники могут заполнять анкеты (/start).\n"
    "Старые анкеты, свайпы и метчи сброшены."
)
ADMIN_RESET_DONE = "🧹 <b>Сброшено:</b> этап закрыт, все данные очищены."
ADMIN_DUMP_EMPTY = "Анкет пока нет."
VERIFY_ALREADY_DONE = "Эта анкета уже обработана другим администратором."


def admin_verification_card(p: Profile) -> str:
    return "\n".join(
        [
            "🕐 <b>Новая анкета на проверке</b>",
            "",
            _card_header(p),
            f"🎯 <b>Хобби:</b> {_esc(p.hobbies)}",
            f"✨ <b>Мечта:</b> {_esc(p.dream)}",
            _contact_line(p),
            f"🆔 uid: {p.user_id}",
        ]
    )


def admin_verdict_card(p: Profile, approved: bool, admin_label: str) -> str:
    verdict = "✅ <b>Одобрена</b>" if approved else "❌ <b>Отклонена</b>"
    return f"{admin_verification_card(p)}\n\n{verdict}: {_esc(admin_label)}"


def admin_dump(
    profiles: list[Profile],
    likes: dict[int, int],
    matches: list[tuple[int, int]],
) -> str:
    if not profiles:
        return ADMIN_DUMP_EMPTY
    lines: list[str] = [f"Анкет: {len(profiles)}. Метчей: {len(matches)}.", ""]
    lines.append("=== Анкеты ===")
    for p in sorted(profiles, key=lambda x: x.user_id):
        handle = f"@{_esc(p.username)}" if p.username else "-"
        combo = f"{_gender_label(p.gender)}/{_looking_label(p.looking_for)}"
        lines.append(
            f"#{p.user_id} {_esc(p.name)} [{combo}] "
            f"{p.age}лет {handle} | лайков: {likes.get(p.user_id, 0)}"
        )
    lines.append("")
    lines.append("=== Метчи ===")
    if not matches:
        lines.append("нет пар")
    else:
        for i, (a, b) in enumerate(sorted(matches), 1):
            lines.append(f"{i}. #{a} 💞 #{b}")
    return "\n".join(lines)


ADMIN_HELP = (
    "🛠 <b>Команды администратора</b> (только в личке с ботом):\n"
    "/first — открыть этап 1: участники могут заполнять анкеты через /start\n"
    "/dump — выгрузка анкет, лайков и метчей\n"
    "/reset — полный сброс (этап + все данные)\n"
    "/help — показать эту справку\n\n"
    "🕐 <b>Верификация:</b> новые анкеты приходят администраторам с кнопками "
    "«✅ Одобрить» / «❌ Отклонить». Пока анкета не одобрена, участник "
    "не виден другим и не может смотреть анкеты. Решение принимает "
    "первый нажавший администратор — его имя появится на карточке у всех.\n\n"
    "<b>Порядок:</b> /first → (участники /start, верификация, /browse) → /dump (опц.) → /reset."
)
