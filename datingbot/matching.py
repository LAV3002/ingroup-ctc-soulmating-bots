from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from datingbot import config
from datingbot.constants import GENDER_F, GENDER_M, LOOKING_SET
from datingbot.models import Profile
from datingbot.questions import weights


@dataclass(frozen=True)
class Match:
    a_uid: int
    b_uid: int
    score: float


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


def similarity(a: Profile, b: Profile, w: dict[str, float] | None = None) -> float:
    """Взвешенное число совпадающих ответов + бонус за близость возраста."""
    if w is None:
        w = weights()
    score = 0.0
    for qid, weight in w.items():
        if a.answers.get(qid) is not None and a.answers.get(qid) == b.answers.get(qid):
            score += weight
    gap = abs(a.age - b.age)
    bonus = config.AGE_PROXIMITY_BONUS - gap * config.AGE_PENALTY_PER_YEAR
    if bonus > 0:
        score += bonus
    return score


def compute_candidates(
    profiles: dict[int, Profile], w: dict[str, float] | None = None
) -> list[Match]:
    if w is None:
        w = weights()
    candidates: list[Match] = []
    for a, b in combinations(profiles.values(), 2):
        if not compatible(a, b):
            continue
        score = similarity(a, b, w)
        candidates.append(Match(a_uid=a.user_id, b_uid=b.user_id, score=score))
    return candidates


def _age_gap(profiles: dict[int, Profile], m: Match) -> int:
    return abs(profiles[m.a_uid].age - profiles[m.b_uid].age)


def assign_pairs(
    profiles: dict[int, Profile], w: dict[str, float] | None = None
) -> list[Match]:
    """Жадное разбиение на непересекающиеся пары: каждому ≤ 1 метч.

    Порядок выбора: выше score, затем меньше разница возрастов,
    затем меньший user_id как тай-брейк.
    """
    candidates = compute_candidates(profiles, w)
    ordered = sorted(
        candidates,
        key=lambda m: (-m.score, _age_gap(profiles, m), m.a_uid, m.b_uid),
    )
    used: set[int] = set()
    pairs: list[Match] = []
    for m in ordered:
        if m.a_uid in used or m.b_uid in used:
            continue
        used.add(m.a_uid)
        used.add(m.b_uid)
        pairs.append(m)
    return pairs


def partner_of(pairs: list[Match], user_id: int) -> int | None:
    for m in pairs:
        if m.a_uid == user_id:
            return m.b_uid
        if m.b_uid == user_id:
            return m.a_uid
    return None
