from __future__ import annotations

from dataclasses import dataclass

from datingbot import config


@dataclass(frozen=True)
class Option:
    id: str
    text: str


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    kind: str  # "text" | "photo"
    options: tuple[Option, ...]
    weight: float = 1.0
    # Для photo-вопросов: список файлов в assets/
    photos: tuple[str, ...] = ()


def _opt(letter: str, text: str) -> Option:
    return Option(id=letter, text=text)


# Текстовые вопросы
Q_MUSIC = Question(
    id="q_music",
    text="Кто милее?",
    kind="text",
    options=(
        _opt("a", "Crystal Castles"),
        _opt("b", "Lil Peep"),
        _opt("c", "Icegergert"),
        _opt("d", "Дайте танк"),
    ),
)

Q_FILM = Question(
    id="q_film",
    text="Кто милее (4)?",
    kind="text",
    options=(
        _opt("a", "Анора"),
        _opt("b", "Трансформеры"),
        _opt("c", "Зверополис"),
        _opt("d", "Бойцовский клуб"),
    ),
)

Q_MARRIAGE = Question(
    id="q_marriage",
    text="Брак по?",
    kind="text",
    options=(
        _opt("a", "Любви"),
        _opt("b", "Расчету"),
    ),
)

Q_VALUE = Question(
    id="q_value",
    text="Кто милее (7)?",
    kind="text",
    options=(
        _opt("a", "Деньги"),
        _opt("b", "Здоровье"),
        _opt("c", "Свобода"),
        _opt("d", "Власть"),
    ),
)

Q_LOVELANG = Question(
    id="q_lovelang",
    text="Язык любви?",
    kind="text",
    options=(
        _opt("a", "Слова"),
        _opt("b", "Время"),
        _opt("c", "Подарки"),
        _opt("d", "Помощь"),
        _opt("e", "Прикосновения"),
    ),
)

Q_DATE = Question(
    id="q_date",
    text="Идеальное свидание?",
    kind="text",
    options=(
        _opt("a", "Сходить в кино"),
        _opt("b", "Сходить в ресторан"),
        _opt("c", "Сходить на выставку"),
        _opt("d", "Сходить на велопрогулку"),
    ),
)

# Фото-вопросы
Q_TRIP = Question(
    id="q_trip",
    text="Моя идеальная поездка — выбери вариант:",
    kind="photo",
    options=(
        _opt("a", "Вариант 1"),
        _opt("b", "Вариант 2"),
        _opt("c", "Вариант 3"),
        _opt("d", "Вариант 4"),
    ),
    photos=("id1.jpg", "id2.jpg", "id3.jpg", "id4.jpg"),
)

Q_CHOOSE = Question(
    id="q_choose",
    text="Что выберешь?",
    kind="photo",
    options=(
        _opt("a", "Вариант 1"),
        _opt("b", "Вариант 2"),
        _opt("c", "Вариант 3"),
        _opt("d", "Вариант 4"),
    ),
    photos=("cv1.jpg", "cv2.jpg", "cv3.jpg", "cv4.jpg"),
)


# Порядок теста
TEST_QUESTIONS: tuple[Question, ...] = (
    Q_MUSIC,
    Q_FILM,
    Q_MARRIAGE,
    Q_VALUE,
    Q_LOVELANG,
    Q_TRIP,
    Q_CHOOSE,
    Q_DATE,
)


def weights() -> dict[str, float]:
    return {q.id: q.weight for q in TEST_QUESTIONS}


def photo_path(filename: str) -> str:
    return str(config.assets_dir() / filename)
