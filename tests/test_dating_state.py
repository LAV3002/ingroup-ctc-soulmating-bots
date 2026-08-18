from __future__ import annotations

import pickle

from datingbot.constants import Stage
from datingbot.models import Profile
from datingbot.state import (
    LIKE,
    PASS,
    all_profiles,
    get_profile,
    get_stage,
    likes_of,
    matches_of,
    pop_verify_msgs,
    record_match,
    record_swipe,
    refresh_username,
    remember_verify_msg,
    remove_profile,
    reset_all,
    reset_profiles,
    save_profile,
    set_stage,
    swipe_action,
    viewed_ids,
)


def _p(uid: int, username: str | None = None) -> Profile:
    return Profile(
        user_id=uid,
        chat_id=uid,
        name=f"u{uid}",
        username=username,
        gender="m",
        age=25,
        looking_for="f",
        hobbies="",
        dream="",
    )


def test_default_stage_is_none():
    bot_data: dict = {}
    assert get_stage(bot_data) == Stage.NONE


def test_stage_unpickles_legacy_second_as_none():
    # Старые pickle-файлы содержали Stage.SECOND — не должны ломать загрузку.
    assert Stage("second") is Stage.NONE


def test_set_and_get_stage():
    bot_data: dict = {}
    set_stage(bot_data, Stage.FIRST)
    assert get_stage(bot_data) == Stage.FIRST


def test_save_and_get_profile():
    bot_data: dict = {}
    save_profile(bot_data, _p(1))
    assert get_profile(bot_data, 1) is not None
    assert get_profile(bot_data, 2) is None


def test_all_profiles_is_copy():
    bot_data: dict = {}
    save_profile(bot_data, _p(1))
    snapshot = all_profiles(bot_data)
    snapshot.clear()
    assert get_profile(bot_data, 1) is not None


def test_record_swipe_and_query():
    bot_data: dict = {}
    record_swipe(bot_data, 1, 2, LIKE)
    record_swipe(bot_data, 1, 3, PASS)
    assert swipe_action(bot_data, 1, 2) == LIKE
    assert swipe_action(bot_data, 1, 3) == PASS
    assert swipe_action(bot_data, 1, 4) is None
    assert viewed_ids(bot_data, 1) == {2, 3}
    assert viewed_ids(bot_data, 2) == set()


def test_likes_of_only_counts_likes():
    bot_data: dict = {}
    record_swipe(bot_data, 1, 2, LIKE)
    record_swipe(bot_data, 1, 3, PASS)
    assert likes_of(bot_data, 1) == {2}


def test_first_swipe_wins():
    bot_data: dict = {}
    record_swipe(bot_data, 1, 2, PASS)
    record_swipe(bot_data, 1, 2, LIKE)
    assert swipe_action(bot_data, 1, 2) == PASS


def test_record_match_symmetric():
    bot_data: dict = {}
    record_match(bot_data, 1, 2)
    assert matches_of(bot_data, 1) == {2}
    assert matches_of(bot_data, 2) == {1}
    assert matches_of(bot_data, 3) == set()


def test_refresh_username():
    p = _p(1)
    assert not refresh_username(p, None)
    assert p.username is None
    assert refresh_username(p, "alice")
    assert p.username == "alice"
    assert not refresh_username(p, "alice")


def test_profile_defaults_unverified():
    assert _p(1).verified is False
    assert _p(1).verified_by is None


def test_profile_unpickles_legacy_without_verification_fields():
    p = _p(1)
    legacy = p.__dict__.copy()
    del legacy["verified"]
    del legacy["verified_by"]
    obj = object.__new__(Profile)
    obj.__setstate__(legacy)
    assert obj.verified is False
    assert obj.verified_by is None


def test_profile_pickle_roundtrip_keeps_verification():
    p = _p(1)
    p.verified = True
    p.verified_by = "@admin (uid=9)"
    restored = pickle.loads(pickle.dumps(p))
    assert restored.verified is True
    assert restored.verified_by == "@admin (uid=9)"


def test_profile_setstate_keeps_existing_verification():
    state = {"verified": True, "verified_by": "@admin (uid=9)"}
    obj = object.__new__(Profile)
    obj.__setstate__(state)
    assert obj.verified is True
    assert obj.verified_by == "@admin (uid=9)"


def test_remember_and_pop_verify_msgs():
    bot_data: dict = {}
    remember_verify_msg(bot_data, 1, 100, 200)
    remember_verify_msg(bot_data, 1, 101, 201)
    assert pop_verify_msgs(bot_data, 1) == [(100, 200), (101, 201)]
    assert pop_verify_msgs(bot_data, 1) == []


def test_remove_profile_clears_traces():
    bot_data: dict = {}
    save_profile(bot_data, _p(1))
    save_profile(bot_data, _p(2))
    record_swipe(bot_data, 1, 2, LIKE)
    record_swipe(bot_data, 2, 1, LIKE)
    record_match(bot_data, 1, 2)
    remember_verify_msg(bot_data, 1, 100, 200)
    remove_profile(bot_data, 1)
    assert get_profile(bot_data, 1) is None
    assert viewed_ids(bot_data, 2) == set()
    assert matches_of(bot_data, 2) == set()
    assert pop_verify_msgs(bot_data, 1) == []
    assert get_profile(bot_data, 2) is not None


def test_reset_profiles_returns_count_and_clears_everything():
    bot_data: dict = {}
    save_profile(bot_data, _p(1))
    save_profile(bot_data, _p(2))
    record_swipe(bot_data, 1, 2, LIKE)
    record_match(bot_data, 1, 2)
    remember_verify_msg(bot_data, 1, 100, 200)
    assert reset_profiles(bot_data) == 2
    assert all_profiles(bot_data) == {}
    assert viewed_ids(bot_data, 1) == set()
    assert matches_of(bot_data, 1) == set()
    assert pop_verify_msgs(bot_data, 1) == []


def test_reset_all_clears_stage_and_data():
    bot_data: dict = {}
    set_stage(bot_data, Stage.FIRST)
    save_profile(bot_data, _p(1))
    record_swipe(bot_data, 1, 2, LIKE)
    record_match(bot_data, 1, 2)
    reset_all(bot_data)
    assert get_stage(bot_data) == Stage.NONE
    assert all_profiles(bot_data) == {}
    assert viewed_ids(bot_data, 1) == set()
    assert matches_of(bot_data, 1) == set()
