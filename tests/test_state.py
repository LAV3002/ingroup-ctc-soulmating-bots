from regabot.constants import Stage
from regabot.models import Participant
from regabot.state import (
    find_badge_in_table,
    find_tables_of_user,
    get_active_table,
    get_profile,
    get_table,
    set_active_table,
    set_profile,
)


def _p(badge: int, uid: int, table: str = "art") -> Participant:
    return Participant(
        chat_id=uid,
        user_id=uid,
        name=f"u{uid}",
        phone="+0",
        username=None,
        table_tag=table,
        badge=badge,
    )


def test_get_table_creates_and_reuses():
    bd: dict = {}
    t1 = get_table(bd, "art")
    t2 = get_table(bd, "art")
    assert t1 is t2
    assert "art" in bd["tables"]


def test_active_table_defaults_to_first_assigned():
    bd: dict = {}
    assert get_active_table(bd, 1, ("art", "converse")) == "art"
    set_active_table(bd, 1, "converse")
    assert get_active_table(bd, 1, ("art", "converse")) == "converse"


def test_active_table_falls_back_when_assignment_changed():
    bd: dict = {}
    set_active_table(bd, 1, "art")
    # админа больше не назначили на art — только на converse
    assert get_active_table(bd, 1, ("converse",)) == "converse"


def test_active_table_empty_assignment():
    bd: dict = {}
    assert get_active_table(bd, 1, ()) is None


def test_find_helpers_single_table():
    bd: dict = {}
    t = get_table(bd, "art")
    t.registrations[5] = _p(5, 100)
    t.stage = Stage.SECOND
    assert find_badge_in_table(t, 100) == 5
    assert find_badge_in_table(t, 999) is None
    assert find_tables_of_user(bd, 100) == [("art", 5)]
    assert find_tables_of_user(bd, 999) == []


def test_user_in_two_tables():
    bd: dict = {}
    get_table(bd, "art").registrations[5] = _p(5, 100, "art")
    get_table(bd, "converse").registrations[7] = _p(7, 100, "converse")
    tags = sorted(t for t, _ in find_tables_of_user(bd, 100))
    assert tags == ["art", "converse"]


def test_each_table_state_is_independent():
    bd: dict = {}
    art = get_table(bd, "art")
    converse = get_table(bd, "converse")
    art.stage = Stage.FIRST
    assert converse.stage == Stage.NONE
    art.registrations[3] = _p(3, 1, "art")
    assert converse.registrations == {}


def test_profile_set_get_and_refresh():
    bd: dict = {}
    assert get_profile(bd, 1) is None
    set_profile(bd, 1, "Alice", "+111", "alice")
    p = get_profile(bd, 1)
    assert p is not None and p.name == "Alice" and p.phone == "+111" and p.username == "alice"
    # refresh username/phone keeps name
    set_profile(bd, 1, "Alice", "+222", None)
    p = get_profile(bd, 1)
    assert p.phone == "+222" and p.username is None


def test_profile_survives_table_reset():
    bd: dict = {}
    set_profile(bd, 1, "Alice", "+111", "alice")
    t = get_table(bd, "art")
    t.registrations[5] = _p(5, 1, "art")
    t.reset_all()
    # профиль остаётся, регистрация стола очищена
    assert get_profile(bd, 1) is not None
    assert find_tables_of_user(bd, 1) == []
