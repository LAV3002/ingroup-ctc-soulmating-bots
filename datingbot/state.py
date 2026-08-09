from __future__ import annotations

from typing import Any

from datingbot.constants import Stage
from datingbot.models import Profile

STAGE_KEY = "dating_stage"
PROFILES_KEY = "dating_profiles"


def get_stage(bot_data: dict[str, Any]) -> Stage:
    stage = bot_data.get(STAGE_KEY)
    if not isinstance(stage, Stage):
        stage = Stage.NONE
        bot_data[STAGE_KEY] = stage
    return stage


def set_stage(bot_data: dict[str, Any], stage: Stage) -> None:
    bot_data[STAGE_KEY] = stage


def _profiles(bot_data: dict[str, Any]) -> dict[int, Profile]:
    profiles = bot_data.get(PROFILES_KEY)
    if not isinstance(profiles, dict):
        profiles = {}
        bot_data[PROFILES_KEY] = profiles
    return profiles


def get_profile(bot_data: dict[str, Any], user_id: int) -> Profile | None:
    profile = _profiles(bot_data).get(user_id)
    return profile if isinstance(profile, Profile) else None


def save_profile(bot_data: dict[str, Any], profile: Profile) -> None:
    _profiles(bot_data)[profile.user_id] = profile


def all_profiles(bot_data: dict[str, Any]) -> dict[int, Profile]:
    return dict(_profiles(bot_data))


def reset_profiles(bot_data: dict[str, Any]) -> int:
    profiles = _profiles(bot_data)
    count = len(profiles)
    profiles.clear()
    return count


def reset_all(bot_data: dict[str, Any]) -> None:
    set_stage(bot_data, Stage.NONE)
    _profiles(bot_data).clear()
