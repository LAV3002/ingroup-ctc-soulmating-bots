from __future__ import annotations

from regabot.models import Participant

# --- Регистрация (/start) ---
ASK_NAME = "Привет! Как тебя зовут? (введи имя текстом)"
NAME_EMPTY = "Пожалуйста, введи имя текстом."
ASK_CONTACT = (
    "Приятно познакомиться, {name}! Нажми кнопку «Поделиться контактом», "
    "чтобы передать номер телефона и аккаунт Telegram."
)
CONTACT_MISSING = "Нужно нажать кнопку «Поделиться контактом» ниже."
CONTACT_NOT_YOURS = "Пожалуйста, поделись своим контактом, а не чужим."
ASK_BADGE = "Введи свой порядковый номер с бейджа (целое число)."
BADGE_INVALID = "Номер должен быть целым положительным числом. Попробуй ещё раз."
BADGE_TAKEN = "Этот номер уже занят за этим столом. Проверь бейдж и введи номер ещё раз."
REGISTRATION_CANCELLED = "Регистрация отменена. Можно начать заново командой /start."


def start_hello(open_tags: list[str], my_tables: list[str], has_profile: bool) -> str:
    lines = ["Привет! Я бот SoulMating.", ""]
    lines.append("Команды участника:")
    lines.append("/reg_for_table [стол] — зарегистрироваться на текущую сессию")
    lines.append("/sympathy [стол] — указать симпатии (на этапе 2)")
    lines.append("")
    if open_tags:
        lines.append("Сейчас открыта регистрация за столы: " + ", ".join(open_tags) + ".")
    else:
        lines.append("Сейчас регистрация закрыта — дождись начала новой сессии.")
    if my_tables:
        lines.append("В этой сессии ты уже зарегистрирован за столы: " + ", ".join(my_tables) + ".")
    if not has_profile:
        lines.append("")
        lines.append("При первой регистрации я попрошу имя и контакт — потом они сохранятся.")
    return "\n".join(lines)


def ask_table(open_tags: str) -> str:
    return f"За каким столом регистрируешься? Сейчас открыты: {open_tags}."


def table_invalid(tags: str) -> str:
    return f"Не знаю такого тега стола. Доступные теги: {tags}."


def table_closed(tag: str, open_tags: str) -> str:
    if open_tags:
        return f"Регистрация за столом {tag} закрыта. Открыты: {open_tags}."
    return f"Регистрация за столом {tag} закрыта."


def already_at_table(tag: str) -> str:
    return f"Ты уже зарегистрирован(а) за столом {tag}."


def no_open_tables() -> str:
    return "Сейчас регистрация закрыта во всех столах. Подождите начала этапа."


def registered(p: Participant) -> str:
    handle = f"@{p.username}" if p.username else "без @username"
    return (
        "Готово! Ты зарегистрирован(а):\n"
        f"- Имя: {p.name}\n"
        f"- Стол: {p.table_tag}\n"
        f"- Номер: {p.badge}\n"
        f"- Telegram: {handle}\n"
        f"- Телефон: {p.phone}\n\n"
        "Ожидай начала этапа выбора симпатий."
    )


# --- Симпатии (/sympathy) ---
NOT_REGISTERED = "Ты нигде не зарегистрирован(а). Сначала /start."
SYMPATHY_FORMAT = "Напиши в одном сообщении: номер приоритет. Например: 12 1"
SYMPATHY_PRIORITY_INVALID = "Приоритет — натуральное число (1, 2, 3, ...). Попробуй ещё раз."
SYMPATHY_TARGET_UNKNOWN = "Участника с таким номером за этим столом нет. Проверь номер."
SYMPATHY_SELF = "Нельзя указать симпатию на самого себя. Выбери другого участника."
SYMPATHY_CLEARED = "Твой список симпатий очищен. Вводи заново."
SYMPATHY_CANCELLED = "Выбор симпатий отменён. Изменения не сохранены."


def sympathy_ambiguous(tables: list[str]) -> str:
    return (
        "Ты зарегистрирован(а) в нескольких столах. Укажи стол:\n"
        + "\n".join(f"/sympathy {t}" for t in tables)
    )


def sympathy_wrong_table(tag: str) -> str:
    return f"Ты не зарегистрирован(а) за столом {tag}."


def sympathy_closed(tag: str) -> str:
    return f"Этап выбора симпатий за столом {tag} сейчас закрыт."


def sympathy_intro(max_sympathies: int) -> str:
    return (
        "Этап выбора СуперМэтчей начался!\n"
        f"Можно выбрать до {max_sympathies} участников.\n"
        "Пиши сообщения в формате: номер приоритет (1 — самый интересен).\n"
        "Пример: 12 1\n\n"
        "Когда закончишь — нажми /done."
    )


def sympathy_progress(entries: list[tuple[int, int]], max_sympathies: int) -> str:
    lines = [f"Записано: {len(entries)}/{max_sympathies}"]
    for target, priority in entries:
        lines.append(f"- номер {target}, приоритет {priority}")
    lines.append("\nВведи следующий или нажми /done для сохранения.")
    return "\n".join(lines)


def sympathy_saved(entries: list[tuple[int, int]]) -> str:
    if not entries:
        return "Симпатии сохранены: ты никого не выбрал(а)."
    lines = ["Симпатии сохранены:"]
    for target, priority in entries:
        lines.append(f"- номер {target}, приоритет {priority}")
    lines.append("\nОжидай результатов. Контакты взаимных метчей пришлём позже.")
    return "\n".join(lines)


# --- Админка ---
ADMIN_NO_REGISTRATIONS = (
    "За активным столом нет зарегистрированных участников. Сначала открой /first."
)

SECOND_NOTIFY = (
    "Регистрация завершена! Переходим к выбору СуперМэтчей.\n"
    "Нажми /sympathy и укажи до трёх понравившихся участников с приоритетом."
)


def use_show(active: str | None, assigned: str) -> str:
    return f"Активный стол: {active}.\nНазначенные тебе столы: {assigned}."


def use_set(tag: str) -> str:
    return f"Активный стол: {tag}."


def use_denied(tag: str, assigned: str) -> str:
    return f"Ты не назначен на стол {tag}. Назначенные: {assigned}."


def admin_first_done(tag: str) -> str:
    return (
        f"Этап 1 открыт для стола {tag}. Регистрация сброшена, "
        "участники могут делать /start и указывать этот стол."
    )


def admin_second_done(tag: str) -> str:
    return f"Этап 2 открыт для стола {tag}. Уведомления участникам отправляются."


def admin_love_already(tag: str) -> str:
    return f"Контакты для стола {tag} уже отправлены. Используй /love_force для повторной отправки."


def admin_reset_done(tag: str) -> str:
    return f"Стол {tag} сброшен: этап закрыт, все данные этого стола очищены."


ADMIN_HELP = (
    "Команды администратора (действуют на активный стол — см. /use):\n"
    "/use <стол> — выбрать активный стол из назначенных тебе\n"
    "/first — начать новую сессию: сбросить стол и открыть регистрацию (/reg_for_table)\n"
    "/second — открыть этап 2 (выбор симпатий), уведомить участников\n"
    "/third — этап 3: посчитать взаимные симпатии, прислать список пар\n"
    "/love — однократно разослать участникам контакты взаимных метчей + идеи встречи\n"
    "/love_force — принудительно разослать контакты повторно\n"
    "/reset — сбросить активный стол (этап и все данные этого стола)\n"
    "/help — показать эту справку\n\n"
    "Порядок: /use → /first → /second → /third → /love → (опц. /love_force) → /reset."
)


def admin_report(matches: list, registrations: dict[int, Participant], tag: str) -> str:
    if not matches:
        return f"Стол {tag}: взаимных симпатий не найдено."

    involved: set[int] = set()
    for m in matches:
        involved.add(m.a_badge)
        involved.add(m.b_badge)

    lines = [f"Стол {tag}. Найдено взаимных метчей: {len(matches)}"]
    lines.append("Участники с метчами: " + ", ".join(str(b) for b in sorted(involved)))
    lines.append("")

    def line(p: Participant) -> str:
        handle = f"@{p.username}" if p.username else "-"
        return f"#{p.badge} {p.name} {handle}"

    for i, m in enumerate(sorted(matches, key=lambda x: (x.a_badge, x.b_badge)), 1):
        a = registrations[m.a_badge]
        b = registrations[m.b_badge]
        flag = " [СуперМэтч]" if m.super_match else ""
        lines.append(f"{i}. {line(a)}  <3  {line(b)}{flag}")

    return "\n".join(lines)


def admin_love_done(sent: int, failed: int) -> str:
    base = f"Контакты отправлены. Доставлено: {sent}."
    if failed:
        base += f" Не доставлено (вероятно, заблокировали бота): {failed}."
    return base


def love_message(
    participant: Participant,
    partners: list[tuple[int, bool]],
    registrations: dict[int, Participant],
    ideas: list[str],
) -> str:
    if not partners:
        return "К сожалению, взаимных симпатий в этот раз не сложилось. Спасибо за участие!"
    lines = [f"У тебя {len(partners)} взаимная симпатия!", ""]
    for badge, is_super in partners:
        other = registrations[badge]
        handle = f"@{other.username}" if other.username else "нет @username"
        tag = " [СуперМэтч]" if is_super else ""
        lines.append(f"- {other.name} — {handle} — тел. {other.phone}{tag}")
    lines.append("")
    if ideas:
        lines.append("Идеи для первой встречи:")
        for idea in ideas:
            lines.append(f"- {idea}")
    else:
        lines.append("Хорошей первой встречи!")
    return "\n".join(lines)
