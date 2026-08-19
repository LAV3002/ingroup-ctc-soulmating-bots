from __future__ import annotations

import html

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.models import Profile

DIVIDER = "━━━━━━━━━━━━"
TOTAL_STEPS = 7


def _esc(value: str) -> str:
    """Escape user input for Telegram's HTML parse mode."""
    return html.escape(value, quote=False)


def _href(value: str) -> str:
    return html.escape(value, quote=True)


def _gender_label(gender: str) -> str:
    return {GENDER_M: "мужчина", GENDER_F: "женщина"}.get(gender, gender)


def _looking_label(looking_for: str) -> str:
    return {
        LOOKING_M: "мужчин",
        LOOKING_F: "женщин",
        LOOKING_MF: "всех",
    }.get(looking_for, looking_for)


def _step(step: int, title: str, body: str, hint: str | None = None) -> str:
    progress = "■" * step + "□" * (TOTAL_STEPS - step)
    parts = [f"<b>{step:02} / {title}</b>", f"<code>{progress}  Шаг {step}/7</code>", "", body]
    if hint:
        parts.extend(["", f"<i>{hint}</i>"])
    return "\n".join(parts)


def _card_header(profile: Profile) -> str:
    return (
        f"<b>{_esc(profile.name.upper())} · {profile.age}</b>\n"
        f"<code>{_gender_label(profile.gender)} / ищет {_looking_label(profile.looking_for)}</code>"
    )


def _card_body(profile: Profile, contact: bool = False) -> str:
    lines = [
        _card_header(profile),
        DIVIDER,
        "<b>ХОББИ / ЧЕМ ЖИВЁТ</b>",
        _esc(profile.hobbies),
        "",
        "<b>МЕЧТА / КУДА ХОЧЕТ</b>",
        _esc(profile.dream),
    ]
    if contact:
        lines.extend(["", DIVIDER, _contact_line(profile)])
    return "\n".join(lines)


def _contact_line(profile: Profile) -> str:
    if profile.username:
        username = _esc(profile.username)
        return (
            "<b>СВЯЗЬ / TELEGRAM</b>\n"
            f'<a href="https://t.me/{_href(profile.username)}">@{username}</a>'
        )
    return "<b>СВЯЗЬ</b>\n@username не указан — обратись к организаторам, они помогут встретиться."


# --- /start and registration ---
START_CLOSED = (
    "<b>SOULMATING / РЕГИСТРАЦИЯ ЗАКРЫТА</b>\n"
    f"{DIVIDER}\n\n"
    "Сейчас анкеты не принимаются: организаторы ещё не открыли регистрацию.\n\n"
    "Когда этап начнётся, вернись по команде /start."
)

ASK_NAME = _step(
    1,
    "ИМЯ",
    "У всякой истории сначала есть имя.\nКак к тебе обращаться?",
    "Напиши имя одной строкой.",
)


def start_open(has_profile: bool) -> str:
    if has_profile:
        return (
            "<b>SOULMATING / ТВОЯ АНКЕТА</b>\n"
            f"{DIVIDER}\n\n"
            "Анкета уже сохранена. Можно продолжить просмотр или изменить детали."
        )
    return (
        "<b>SOULMATING / СЛУЧАЙ</b>\n"
        "Заполни анкету — и бот покажет людей, с которыми интерес может быть взаимным.\n\n"
        f"{ASK_NAME}"
    )


def profile_edit_intro() -> str:
    return (
        "<b>SOULMATING / НОВАЯ РЕДАКЦИЯ</b>\n"
        f"{DIVIDER}\n\n"
        "Старая анкета останется на месте, пока новая не будет закончена. "
        "После сохранения она снова пройдёт проверку.\n\n"
        f"{ASK_NAME}"
    )


NAME_EMPTY = "<b>НУЖЕН ТЕКСТ</b>\nИмя не может состоять из одного молчания. Попробуй ещё раз."
NAME_TOO_LONG = "<b>КОРОЧЕ</b>\nДо {max} знаков: подпись, не автобиография."
ASK_GENDER = _step(2, "ПОЛ", "Формальности — короткая часть знакомства. Выбери вариант ниже.")
ASK_AGE = _step(
    3,
    "ВОЗРАСТ",
    "В паспорте это число. Здесь — полезная координата. Сколько тебе лет?",
    "Только целое число.",
)
AGE_INVALID = "<b>НЕ ЧИСЛО</b>\nНужен возраст целым числом — например, <code>27</code>."
AGE_OUT_OF_RANGE = "<b>ЗА ПРЕДЕЛАМИ</b>\nВозраст должен быть от {min} до {max}. Введи другое число."
ASK_LOOKING_FOR = _step(
    4, "КОГО ИЩЕШЬ", "Кому должен показать тебя этот небольшой механизм случая?"
)
ASK_PHOTO = _step(
    5,
    "ПОРТРЕТ",
    "Пришли одну фотографию, где тебя легко узнать. Фото обязательно.",
    "Её увидят модераторы и подходящие тебе участники.",
)
PHOTO_INVALID = (
    "<b>НУЖНО ФОТО</b>\nОтправь изображение как фотографию — без него анкета не продолжится."
)
PHOTO_SAVED_ACK = "<b>ПОРТРЕТ ПРИНЯТ</b>"
ASK_HOBBIES = _step(
    6,
    "ЧЕМ ЖИВЁШЬ",
    "Что удерживает твоё внимание, когда никто не требует быть полезным?",
    "Музыка, бег, плёнка, книги — конкретика помогает начать разговор. До {max} знаков.",
)
ASK_DREAM = _step(
    7,
    "КУДА ХОЧЕШЬ",
    "Назови мечту, ради которой будущее стоит своего ожидания.",
    "Одна честная мысль. До {max} знаков.",
)
TEXT_EMPTY = "<b>НУЖЕН ТЕКСТ</b>\nЗдесь пусто. Напиши хотя бы одну строку."
TEXT_TOO_LONG = "<b>КОРОЧЕ</b>\nОтвет должен уместиться в {max} знаков."
REGISTRATION_CANCELLED = (
    "<b>АНКЕТА НЕ ИЗМЕНЕНА</b>\n"
    "Черновик исчез; всё остальное осталось на месте. Начать снова — /start."
)


def profile_overview(profile: Profile) -> str:
    status = "ПРОВЕРЕНА" if profile.verified else "НА ПРОВЕРКЕ"
    return (
        f"<b>ТВОЯ АНКЕТА / {status}</b>\n\n"
        f"{_card_body(profile)}\n\n"
        "<i>Изменённая анкета снова отправится модераторам.</i>"
    )


def profile_saved(profile: Profile) -> str:
    return (
        "<b>АНКЕТА / ПРИНЯТА</b>\n"
        f"{DIVIDER}\n\n"
        f"{_card_body(profile)}\n\n"
        "Теперь — короткая проверка. Когда анкета станет видна другим, бот напишет сам."
    )


PROFILE_PENDING = (
    "<b>АНКЕТА / НА ПРОВЕРКЕ</b>\n"
    f"{DIVIDER}\n\n"
    "Она находится между отправкой и появлением — обычное место для новых вещей. "
    "Мы напишем, как только проверка закончится."
)
VERIFICATION_APPROVED = (
    "<b>АНКЕТА / ОПУБЛИКОВАНА</b>\n"
    f"{DIVIDER}\n\n"
    "Проверка закончена. Теперь можно смотреть подходящие анкеты и отмечать "
    "понравившихся людей."
)
VERIFICATION_REJECTED = (
    "<b>АНКЕТА / НУЖНА ДРУГАЯ РЕДАКЦИЯ</b>\n"
    f"{DIVIDER}\n\n"
    "Эту версию не удалось опубликовать. Исправь детали и попробуй снова: /start."
)


# --- Browsing ---
def swipe_card(profile: Profile) -> str:
    return _card_body(profile)


BROWSE_EMPTY = (
    "<b>ПОКА — ВСЁ</b>\n"
    f"{DIVIDER}\n\n"
    "Все подходящие анкеты просмотрены. Новые люди появляются без расписания; "
    "проверь ещё раз позже."
)
PROFILE_REQUIRED = (
    "<b>СНАЧАЛА — АНКЕТА</b>\n"
    f"{DIVIDER}\n\n"
    "Чтобы видеть других, сначала расскажи о себе. Начать — /start."
)
BROWSE_STOPPED = (
    "<b>ПАУЗА</b>\nЛента остановлена. Она продолжится с нового человека, когда ты вернёшься."
)
SWIPE_LIKED = "Выбрано: да"
SWIPE_PASSED = "Выбрано: дальше"
SWIPE_STOPPED_TOAST = "Пауза"


# --- Matches ---
def match_message(partner: Profile) -> str:
    return (
        "<b>ВЗАИМНО / МЕТЧ</b>\n"
        f"{DIVIDER}\n\n"
        "Среди всех возможных «мимо» вы оба выбрали «да».\n\n"
        f"{_card_body(partner, contact=True)}\n\n"
        "<b>ПЕРВЫЙ ХОД</b>\n"
        "Спроси не «как дела», а какой день человек хотел бы повторить."
    )


# --- Admin ---
ADMIN_FIRST_DONE = (
    "<b>ЭТАП 1 / ОТКРЫТ</b>\n\n"
    "Участники могут заполнять анкеты через /start. Старые анкеты, свайпы и метчи сброшены."
)
ADMIN_RESET_DONE = "<b>СБРОШЕНО</b>\nЭтап закрыт, анкеты и реакции удалены."
ADMIN_DUMP_EMPTY = "Анкет пока нет."
VERIFY_ALREADY_DONE = "Эту анкету уже обработал другой администратор."


def admin_verification_card(profile: Profile) -> str:
    return "\n".join(
        [
            "<b>МОДЕРАЦИЯ / НОВАЯ АНКЕТА</b>",
            DIVIDER,
            _card_header(profile),
            "",
            f"<b>ХОББИ / ЧЕМ ЖИВЁТ</b>\n{_esc(profile.hobbies)}",
            "",
            f"<b>МЕЧТА / КУДА ХОЧЕТ</b>\n{_esc(profile.dream)}",
            "",
            _contact_line(profile),
            f"<code>uid: {profile.user_id}</code>",
        ]
    )


def admin_verdict_card(profile: Profile, approved: bool, admin_label: str) -> str:
    verdict = "✅ <b>Одобрена</b>" if approved else "❌ <b>Отклонена</b>"
    return f"{admin_verification_card(profile)}\n\n{verdict}: {_esc(admin_label)}"


def admin_dump(
    profiles: list[Profile],
    likes: dict[int, int],
    matches: list[tuple[int, int]],
) -> str:
    if not profiles:
        return ADMIN_DUMP_EMPTY
    lines: list[str] = [f"Анкет: {len(profiles)}. Метчей: {len(matches)}.", ""]
    lines.append("=== Анкеты ===")
    for profile in sorted(profiles, key=lambda item: item.user_id):
        handle = f"@{_esc(profile.username)}" if profile.username else "-"
        combination = f"{_gender_label(profile.gender)}/{_looking_label(profile.looking_for)}"
        lines.append(
            f"#{profile.user_id} {_esc(profile.name)} [{combination}] "
            f"{profile.age} лет {handle} | лайков: {likes.get(profile.user_id, 0)}"
        )
    lines.extend(["", "=== Метчи ==="])
    if not matches:
        lines.append("нет пар")
    else:
        for index, (first, second) in enumerate(sorted(matches), 1):
            lines.append(f"{index}. #{first} ↔ #{second}")
    return "\n".join(lines)


ADMIN_HELP = (
    "<b>АДМИН / КОМАНДЫ</b>\n"
    "/first — открыть приём анкет и очистить прошлую сессию\n"
    "/dump — анкеты, лайки и метчи\n"
    "/reset — закрыть этап и удалить данные\n"
    "/help — эта справка\n\n"
    "<b>МОДЕРАЦИЯ</b>\n"
    "Новая анкета приходит с кнопками «Одобрить» и «Отклонить». До одобрения участник "
    "не виден другим и не может листать анкеты. Решение фиксируется за первым нажавшим "
    "администратором.\n\n"
    "<b>ПОРЯДОК</b>\n"
    "/first → анкеты и модерация → /browse → /dump при необходимости → /reset"
)
