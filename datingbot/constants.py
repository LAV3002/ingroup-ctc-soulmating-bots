from __future__ import annotations

from enum import StrEnum


class Stage(StrEnum):
    NONE = "none"
    FIRST = "first"

    @classmethod
    def _missing_(cls, value: object) -> Stage | None:
        # Совместимость со старыми pickle-файлами, где существовал Stage.SECOND.
        if value == "second":
            return cls.NONE
        return None


# Пол
GENDER_M = "m"
GENDER_F = "f"
GENDERS: tuple[str, ...] = (GENDER_M, GENDER_F)

# Кого ищет
LOOKING_M = "m"
LOOKING_F = "f"
LOOKING_MF = "mf"
LOOKING_FOR: tuple[str, ...] = (LOOKING_M, LOOKING_F, LOOKING_MF)

# Разрешённые комбинации «пол A интересен B»: B.gender должен быть в множестве.
# Т.е. A ищет {набор полов}; совместимость требует взаимности.
LOOKING_SET: dict[str, frozenset[str]] = {
    LOOKING_M: frozenset({GENDER_M}),
    LOOKING_F: frozenset({GENDER_F}),
    LOOKING_MF: frozenset({GENDER_M, GENDER_F}),
}
