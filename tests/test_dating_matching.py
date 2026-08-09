from __future__ import annotations

from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M, LOOKING_MF
from datingbot.matching import assign_pairs, compatible, partner_of, similarity
from datingbot.models import Profile
from datingbot.questions import weights


def _p(
    uid: int,
    gender: str = GENDER_M,
    looking: str = LOOKING_F,
    age: int = 25,
    answers: dict[str, str] | None = None,
) -> Profile:
    return Profile(
        user_id=uid,
        chat_id=uid,
        name=f"u{uid}",
        phone="+0",
        username=None,
        gender=gender,
        age=age,
        looking_for=looking,
        hobbies="",
        dream="",
        answers=dict(answers or {}),
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


def test_similarity_counts_matching_answers_weighted():
    w = weights()
    a = _p(1, answers={k: "a" for k in w})
    b_same = _p(2, answers={k: "a" for k in w})
    b_diff = _p(2, answers={k: "b" for k in w})
    assert similarity(a, b_same, w) > similarity(a, b_diff, w)


def test_similarity_age_bonus_closer_is_higher():
    w = weights()
    base = {k: "a" for k in w}
    a = _p(1, age=25, answers=base)
    near = _p(2, age=26, answers=base)
    far = _p(3, age=40, answers=base)
    assert similarity(a, near, w) > similarity(a, far, w)


def test_assign_pairs_disjoint():
    profiles = {
        1: _p(1, GENDER_M, LOOKING_F, answers={"q_music": "a"}),
        2: _p(2, GENDER_F, LOOKING_M, answers={"q_music": "a"}),
        3: _p(3, GENDER_M, LOOKING_F, answers={"q_music": "a"}),
    }
    pairs = assign_pairs(profiles)
    used = [uid for m in pairs for uid in (m.a_uid, m.b_uid)]
    assert len(used) == len(set(used))


def test_assign_pairs_picks_higher_score():
    profiles = {
        1: _p(1, GENDER_M, LOOKING_F, answers={"q_music": "a"}),
        2: _p(2, GENDER_F, LOOKING_M, answers={"q_music": "a"}),  # полный совпад с 1
        3: _p(3, GENDER_F, LOOKING_M, answers={"q_music": "b"}),  # меньше совпадений
    }
    pairs = assign_pairs(profiles)
    assert len(pairs) == 1
    assert partner_of(pairs, 1) == 2


def test_assign_pairs_unmatched_when_no_compatible():
    profiles = {
        1: _p(1, GENDER_M, LOOKING_M),
        2: _p(2, GENDER_F, LOOKING_F),
    }
    assert assign_pairs(profiles) == []


def test_assign_pairs_odd_count_leaves_one_unmatched():
    profiles = {
        1: _p(1, GENDER_M, LOOKING_F),
        2: _p(2, GENDER_F, LOOKING_M),
        3: _p(3, GENDER_M, LOOKING_F),
    }
    pairs = assign_pairs(profiles)
    assert len(pairs) == 1
    used = {uid for m in pairs for uid in (m.a_uid, m.b_uid)}
    assert len(used) == 2


def test_each_user_at_most_one_match_with_mf():
    profiles = {
        1: _p(1, GENDER_M, LOOKING_MF, answers={"q_music": "a"}),
        2: _p(2, GENDER_F, LOOKING_MF, answers={"q_music": "a"}),
        3: _p(3, GENDER_F, LOOKING_MF, answers={"q_music": "a"}),
    }
    pairs = assign_pairs(profiles)
    used = [uid for m in pairs for uid in (m.a_uid, m.b_uid)]
    assert len(used) == len(set(used))
    assert partner_of(pairs, 1) is not None
