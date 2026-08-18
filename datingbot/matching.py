from __future__ import annotations

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_SET
from datingbot.models import Profile


def compatible(a: Profile, b: Profile) -> bool:
    """Жёсткий фильтр по полу и ориентации: взаимная совместимость.

    A ищет LOOKING_SET[a.looking_for]; B должен быть этого пола,
    и симметрично B должен искать пол A.
    """
    if a.gender not in (GENDER_M, GENDER_F) or b.gender not in (GENDER_M, GENDER_F):
        return False
    a_wants = LOOKING_SET.get(a.looking_for, frozenset())
    b_wants = LOOKING_SET.get(b.looking_for, frozenset())
    if not a_wants or not b_wants:
        return False
    return b.gender in a_wants and a.gender in b_wants


def candidates_for(
    profile: Profile,
    profiles: dict[int, Profile],
    viewed: set[int],
) -> list[Profile]:
    """Анкеты для свайпа: подтверждённые, совместимые, ещё не просмотренные.

    Неподтверждённые админом анкеты другим не показываются.
    Порядок детерминированный (по user_id), чтобы не зависеть от порядка dict.
    """
    return [
        p
        for uid, p in sorted(profiles.items())
        if uid != profile.user_id
        and uid not in viewed
        and p.verified
        and compatible(profile, p)
    ]
