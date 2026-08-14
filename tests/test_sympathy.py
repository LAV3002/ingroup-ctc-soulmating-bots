from regabot.handlers.sympathy import add_entry, build_conversation


def test_sympathy_is_entry_point_and_fallback():
    conv = build_conversation()
    entry_commands = {
        cmd for h in conv.entry_points for cmd in getattr(h, "commands", frozenset())
    }
    fallback_commands = {
        cmd for h in conv.fallbacks for cmd in getattr(h, "commands", frozenset())
    }
    assert "sympathy" in entry_commands
    assert "sympathy" in fallback_commands
    assert "sympathy_done" in fallback_commands
    assert "done" not in fallback_commands
    assert "done" not in entry_commands


def test_add_entry_sorts_descending_by_priority():
    entries: list[tuple[int, int]] = []
    entries = add_entry(entries, 5, 1)
    entries = add_entry(entries, 12, 2)
    entries = add_entry(entries, 8, 3)
    assert entries == [(8, 3), (12, 2), (5, 1)]


def test_add_entry_keeps_priority_attached_after_sort():
    entries = add_entry([], 5, 1)
    entries = add_entry(entries, 12, 2)
    assert entries == [(12, 2), (5, 1)]


def test_add_entry_replaces_existing_target_same_priority():
    entries = [(8, 3), (12, 2)]
    entries = add_entry(entries, 12, 2)
    assert [t for (t, _) in entries] == [8, 12]
    assert entries[0] == (8, 3)
    assert entries[1] == (12, 2)


def test_add_entry_replaces_existing_target_new_priority():
    entries = [(8, 3), (5, 1)]
    entries = add_entry(entries, 5, 2)
    assert [t for (t, _) in entries] == [8, 5]
    assert entries[0] == (8, 3)
    assert entries[1] == (5, 2)


def test_add_entry_single_entry():
    assert add_entry([], 7, 1) == [(7, 1)]
