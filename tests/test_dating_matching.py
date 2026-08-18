from __future__ import annotations

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.matching import candidates_for, compatible
from datingbot.models import Profile


def _p(
    uid: int,
    gender: str = GENDER_M,
    looking: str = LOOKING_F,
    age: int = 25,
    verified: bool = True,
) -> Profile:
    return Profile(
        user_id=uid,
        chat_id=uid,
        name=f"u{uid}",
        username=None,
        gender=gender,
        age=age,
        looking_for=looking,
        hobbies="",
        dream="",
        verified=verified,
    )


def test_compatible_hetero_mutual():
    a = _p(1, GENDER_M, LOOKING_F)
    b = _p(2, GENDER_F, LOOKING_M)
    assert compatible(a, b)
    assert compatible(b, a)


def test_compatible_bi_and_same_sex():
    a = _p(1, GENDER_M, LOOKING_M)
    b = _p(2, GENDER_M, LOOKING_M)
    assert compatible(a, b)
    c = _p(3, GENDER_F, LOOKING_MF)
    d = _p(4, GENDER_M, LOOKING_MF)
    assert compatible(c, d)


def test_incompatible_orientation_mismatch():
    a = _p(1, GENDER_M, LOOKING_M)  # ищет мужчин
    b = _p(2, GENDER_F, LOOKING_M)  # женщина, ищет мужчин -> не взаимно
    assert not compatible(a, b)


def test_incompatible_when_not_looked_for():
    a = _p(1, GENDER_M, LOOKING_M)
    b = _p(2, GENDER_F, LOOKING_F)
    assert not compatible(a, b)


def test_candidates_for_filters_self_incompatible_and_viewed():
    me = _p(1, GENDER_M, LOOKING_F)
    ok1 = _p(2, GENDER_F, LOOKING_M)
    ok2 = _p(3, GENDER_F, LOOKING_MF)
    incompatible = _p(4, GENDER_M, LOOKING_M)  # мужчины мне не подходят
    myself = me
    profiles = {1: myself, 2: ok1, 3: ok2, 4: incompatible}
    result = candidates_for(me, profiles, viewed=set())
    assert [p.user_id for p in result] == [2, 3]


def test_candidates_for_excludes_viewed():
    me = _p(1, GENDER_M, LOOKING_F)
    ok1 = _p(2, GENDER_F, LOOKING_M)
    ok2 = _p(3, GENDER_F, LOOKING_M)
    profiles = {1: me, 2: ok1, 3: ok2}
    result = candidates_for(me, profiles, viewed={2})
    assert [p.user_id for p in result] == [3]


def test_candidates_for_excludes_unverified():
    me = _p(1, GENDER_M, LOOKING_F)
    unverified = _p(2, GENDER_F, LOOKING_M, verified=False)
    ok = _p(3, GENDER_F, LOOKING_M)
    profiles = {1: me, 2: unverified, 3: ok}
    result = candidates_for(me, profiles, viewed=set())
    assert [p.user_id for p in result] == [3]


def test_candidates_for_empty_when_all_viewed():
    me = _p(1, GENDER_M, LOOKING_F)
    ok1 = _p(2, GENDER_F, LOOKING_M)
    profiles = {1: me, 2: ok1}
    assert candidates_for(me, profiles, viewed={2}) == []
