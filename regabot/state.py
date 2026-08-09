from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from regabot.constants import Stage
from regabot.models import Participant

TABLES_KEY = "tables"
ACTIVE_KEY = "admin_active"


@dataclass
class TableGame:
    stage: Stage = Stage.NONE
    registrations: dict[int, Participant] = field(default_factory=dict)
    sympathies: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    love_sent: bool = False

    def reset_all(self) -> None:
        self.stage = Stage.NONE
        self.registrations.clear()
        self.sympathies.clear()
        self.love_sent = False


def _tables(bot_data: dict[str, Any]) -> dict[str, TableGame]:
    tables = bot_data.get(TABLES_KEY)
    if not isinstance(tables, dict):
        tables = {}
        bot_data[TABLES_KEY] = tables
    return tables


def get_table(bot_data: dict[str, Any], tag: str) -> TableGame:
    tables = _tables(bot_data)
    game = tables.get(tag)
    if not isinstance(game, TableGame):
        game = TableGame()
        tables[tag] = game
    return game


def get_active_table(
    bot_data: dict[str, Any], user_id: int, assigned: tuple[str, ...]
) -> str | None:
    if not assigned:
        return None
    active_map = bot_data.get(ACTIVE_KEY)
    if not isinstance(active_map, dict):
        active_map = {}
        bot_data[ACTIVE_KEY] = active_map
    active = active_map.get(user_id)
    if active in assigned:
        return active
    active = assigned[0]
    active_map[user_id] = active
    return active


def set_active_table(bot_data: dict[str, Any], user_id: int, tag: str) -> None:
    active_map = bot_data.get(ACTIVE_KEY)
    if not isinstance(active_map, dict):
        active_map = {}
        bot_data[ACTIVE_KEY] = active_map
    active_map[user_id] = tag


def find_badge_in_table(table: TableGame, user_id: int) -> int | None:
    for badge, participant in table.registrations.items():
        if participant.user_id == user_id:
            return badge
    return None


def find_tables_of_user(
    bot_data: dict[str, Any], user_id: int
) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for tag, table in _tables(bot_data).items():
        badge = find_badge_in_table(table, user_id)
        if badge is not None:
            result.append((tag, badge))
    return result


@dataclass
class Profile:
    name: str
    phone: str
    username: str | None


PROFILES_KEY = "profiles"


def _profiles(bot_data: dict[str, Any]) -> dict[int, Profile]:
    profiles = bot_data.get(PROFILES_KEY)
    if not isinstance(profiles, dict):
        profiles = {}
        bot_data[PROFILES_KEY] = profiles
    return profiles


def get_profile(bot_data: dict[str, Any], user_id: int) -> Profile | None:
    profile = _profiles(bot_data).get(user_id)
    return profile if isinstance(profile, Profile) else None


def set_profile(
    bot_data: dict[str, Any],
    user_id: int,
    name: str,
    phone: str,
    username: str | None,
) -> None:
    _profiles(bot_data)[user_id] = Profile(name=name, phone=phone, username=username)
