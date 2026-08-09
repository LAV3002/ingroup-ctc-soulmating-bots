from __future__ import annotations

from datingbot.constants import Stage
from datingbot.models import Profile
from datingbot.state import (
    all_profiles,
    get_profile,
    get_stage,
    reset_all,
    reset_profiles,
    save_profile,
    set_stage,
)


def _p(uid: int) -> Profile:
    return Profile(
        user_id=uid,
        chat_id=uid,
        name=f"u{uid}",
        phone="+0",
        username=None,
        gender="m",
        age=25,
        looking_for="f",
        hobbies="",
        dream="",
    )


def test_default_stage_is_none():
    bot_data: dict = {}
    assert get_stage(bot_data) == Stage.NONE


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


def test_reset_profiles_returns_count_and_clears():
    bot_data: dict = {}
    save_profile(bot_data, _p(1))
    save_profile(bot_data, _p(2))
    assert reset_profiles(bot_data) == 2
    assert all_profiles(bot_data) == {}


def test_reset_all_clears_stage_and_profiles():
    bot_data: dict = {}
    set_stage(bot_data, Stage.FIRST)
    save_profile(bot_data, _p(1))
    reset_all(bot_data)
    assert get_stage(bot_data) == Stage.NONE
    assert all_profiles(bot_data) == {}
