from __future__ import annotations

from typing import Any

from datingbot.constants import Stage
from datingbot.models import Profile

STAGE_KEY = "dating_stage"
PROFILES_KEY = "dating_profiles"
SWIPES_KEY = "dating_swipes"
MATCHES_KEY = "dating_matches"
VERIFY_MSGS_KEY = "dating_verify_msgs"

LIKE = "like"
PASS = "pass"


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


def remove_profile(bot_data: dict[str, Any], user_id: int) -> None:
    """Удаляет анкету и все её следы: свайпы, метчи и ссылки на карточки верификации."""
    _profiles(bot_data).pop(user_id, None)
    swipes = _swipes(bot_data)
    swipes.pop(user_id, None)
    for uid in swipes:
        swipes[uid].pop(user_id, None)
    matches = _matches(bot_data)
    matches.pop(user_id, None)
    for uid in matches:
        matches[uid].discard(user_id)
    pop_verify_msgs(bot_data, user_id)


def _verify_msgs(bot_data: dict[str, Any]) -> dict[int, list[tuple[int, int]]]:
    msgs = bot_data.get(VERIFY_MSGS_KEY)
    if not isinstance(msgs, dict):
        msgs = {}
        bot_data[VERIFY_MSGS_KEY] = msgs
    return msgs


def remember_verify_msg(
    bot_data: dict[str, Any], user_id: int, chat_id: int, message_id: int
) -> None:
    _verify_msgs(bot_data).setdefault(user_id, []).append((chat_id, message_id))


def pop_verify_msgs(
    bot_data: dict[str, Any], user_id: int
) -> list[tuple[int, int]]:
    return _verify_msgs(bot_data).pop(user_id, [])


def _swipes(bot_data: dict[str, Any]) -> dict[int, dict[int, str]]:
    swipes = bot_data.get(SWIPES_KEY)
    if not isinstance(swipes, dict):
        swipes = {}
        bot_data[SWIPES_KEY] = swipes
    return swipes


def _matches(bot_data: dict[str, Any]) -> dict[int, set[int]]:
    matches = bot_data.get(MATCHES_KEY)
    if not isinstance(matches, dict):
        matches = {}
        bot_data[MATCHES_KEY] = matches
    return matches


def record_swipe(bot_data: dict[str, Any], user_id: int, target_id: int, action: str) -> None:
    """Запоминает свайп (like/pass). Первый свайп выигрывает, повторы игнорируются."""
    _swipes(bot_data).setdefault(user_id, {}).setdefault(target_id, action)


def swipe_action(bot_data: dict[str, Any], user_id: int, target_id: int) -> str | None:
    return _swipes(bot_data).get(user_id, {}).get(target_id)


def viewed_ids(bot_data: dict[str, Any], user_id: int) -> set[int]:
    return set(_swipes(bot_data).get(user_id, {}))


def likes_of(bot_data: dict[str, Any], user_id: int) -> set[int]:
    return {
        target
        for target, action in _swipes(bot_data).get(user_id, {}).items()
        if action == LIKE
    }


def record_match(bot_data: dict[str, Any], a_uid: int, b_uid: int) -> None:
    matches = _matches(bot_data)
    matches.setdefault(a_uid, set()).add(b_uid)
    matches.setdefault(b_uid, set()).add(a_uid)


def matches_of(bot_data: dict[str, Any], user_id: int) -> set[int]:
    return set(_matches(bot_data).get(user_id, set()))


def refresh_username(profile: Profile, username: str | None) -> bool:
    """Обновляет @username в анкете (они меняются со временем). True, если изменилось."""
    if username and username != profile.username:
        profile.username = username
        return True
    return False


def reset_profiles(bot_data: dict[str, Any]) -> int:
    profiles = _profiles(bot_data)
    count = len(profiles)
    profiles.clear()
    _swipes(bot_data).clear()
    _matches(bot_data).clear()
    _verify_msgs(bot_data).clear()
    return count


def reset_all(bot_data: dict[str, Any]) -> None:
    set_stage(bot_data, Stage.NONE)
    _profiles(bot_data).clear()
    _swipes(bot_data).clear()
    _matches(bot_data).clear()
    _verify_msgs(bot_data).clear()
