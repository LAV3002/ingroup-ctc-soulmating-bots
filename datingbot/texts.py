from __future__ import annotations

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.models import Profile

# --- /start / регистрация ---
START_CLOSED = (
    "Привет! Я бот-знакомства SoulMating Dating.\n"
    "Сейчас регистрация закрыта — дождись начала ивента."
)


def start_open(has_profile: bool) -> str:
    if has_profile:
        return "С возвращением! Твоя анкета уже заполнена. Жди начала подбора метчей."
    return (
        "Привет! Я бот-знакомства SoulMating Dating.\n"
        "Давай заполним анкету. Как тебя зовут? (введи имя текстом)"
    )


NAME_EMPTY = "Пожалуйста, введи имя текстом."
ASK_CONTACT = (
    "Приятно познакомиться, {name}! Нажми кнопку «Поделиться контактом», "
    "чтобы передать номер телефона и аккаунт Telegram."
)
CONTACT_MISSING = "Нужно нажать кнопку «Поделиться контактом» ниже."
CONTACT_NOT_YOURS = "Пожалуйста, поделись своим контактом, а не чужим."
ASK_GENDER = "Укажи свой пол:"
ASK_AGE = "Укажи свой возраст (целое число):"
AGE_INVALID = "Возраст должен быть целым числом. Попробуй ещё раз."
AGE_OUT_OF_RANGE = "Возраст должен быть от {min} до {max}. Попробуй ещё раз."
ASK_LOOKING_FOR = "Кого ты ищешь?"
ASK_PHOTO = (
    "Прикрепи своё фото (необязательно). "
    "Отправь фото или нажми «Пропустить фото»."
)
PHOTO_INVALID = "Пожалуйста, отправь фото или нажми «Пропустить фото»."
ASK_HOBBIES = "Расскажи о своих хобби (свободным текстом):"
ASK_DREAM = "Какая твоя главная мечта в жизни? (свободным текстом):"
TEXT_EMPTY = "Пожалуйста, введи ответ текстом."
REGISTRATION_CANCELLED = "Анкета отменена. Можно начать заново командой /start."


def profile_saved(p: Profile) -> str:
    return (
        "Анкета сохранена! Спасибо.\n\n"
        f"Имя: {p.name}\n"
        f"Пол: {_gender_label(p.gender)}\n"
        f"Возраст: {p.age}\n"
        f"Ищу: {_looking_label(p.looking_for)}\n"
        f"Хобби: {p.hobbies}\n"
        f"Мечта: {p.dream}\n"
        f"Фото: {'есть' if p.photo_file_id else 'нет'}\n\n"
        "Ожидай начала подбора метчей."
    )


def _gender_label(g: str) -> str:
    return "М" if g == GENDER_M else "Ж" if g == GENDER_F else g


def _looking_label(lf: str) -> str:
    return {LOOKING_M: "М", LOOKING_F: "Ж", LOOKING_MF: "М/Ж"}.get(lf, lf)


# --- Рассылка метчей ---
def match_intro(partner: Profile) -> str:
    handle = f"@{partner.username}" if partner.username else "без @username"
    lines = [
        "У тебя метч! 🎉",
        "",
        f"Имя: {partner.name}",
        f"Пол: {_gender_label(partner.gender)}",
        f"Возраст: {partner.age}",
        f"Ищет: {_looking_label(partner.looking_for)}",
        f"Хобби: {partner.hobbies}",
        f"Мечта: {partner.dream}",
        f"Telegram: {handle}",
        f"Телефон: {partner.phone}",
    ]
    return "\n".join(lines)


def no_match_message() -> str:
    return "К сожалению, в этот раз подходящего метча не нашлось. Спасибо за участие!"


# --- Админка ---
ADMIN_NOT_ENOUGH = (
    "Недостаточно анкет для подбора (нужно минимум 2). Сделай /first и дождись анкет."
)

ADMIN_FIRST_DONE = (
    "Этап 1 открыт: участники могут заполнять анкеты (/start). Старые анкеты сброшены."
)
ADMIN_RESET_DONE = "Сброшено: этап закрыт, все анкетные данные очищены."
ADMIN_DUMP_EMPTY = "Анкет пока нет."


def admin_dump(profiles: list[Profile], pairs: list) -> str:
    if not profiles:
        return ADMIN_DUMP_EMPTY
    lines: list[str] = [f"Анкет: {len(profiles)}. Пар-метчей: {len(pairs)}.", ""]
    lines.append("=== Анкеты ===")
    for p in sorted(profiles, key=lambda x: x.user_id):
        handle = f"@{p.username}" if p.username else "-"
        ans = ", ".join(f"{k}={v}" for k, v in sorted(p.answers.items()))
        lines.append(
            f"#{p.user_id} {p.name} [{_gender_label(p.gender)}/{_looking_label(p.looking_for)}] "
            f"{p.age}лет {handle} | {ans}"
        )
    lines.append("")
    lines.append("=== Метчи ===")
    if not pairs:
        lines.append("нет пар")
    else:
        for i, m in enumerate(sorted(pairs, key=lambda x: (-x.score, x.a_uid)), 1):
            lines.append(f"{i}. #{m.a_uid} <3 #{m.b_uid}  score={m.score:.2f}")
    return "\n".join(lines)


def admin_second_done(sent: int, failed: int, pairs: int) -> str:
    base = f"Подбор выполнен. Пар: {pairs}. Доставлено сообщений: {sent}."
    if failed:
        base += f" Не доставлено (вероятно, заблокировали бота): {failed}."
    return base


ADMIN_HELP = (
    "Команды администратора (только в личке с ботом):\n"
    "/first — открыть этап 1: участники могут заполнять анкеты через /start\n"
    "/second — подобрать метчи и разослать участникам анкеты их пар\n"
    "/dump — выгрузка анкет и текущей кластеризации\n"
    "/reset — полный сброс (этап + все анкеты)\n"
    "/help — показать эту справку\n\n"
    "Порядок: /first → (участники /start) → /dump (опц.) → /second → /reset."
)
