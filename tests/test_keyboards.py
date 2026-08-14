from regabot.keyboards import sympathy_table_keyboard, use_table_keyboard


def _buttons(markup):
    return [btn.text for row in markup.inline_keyboard for btn in row]


def _callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_use_table_keyboard_callbacks_and_active_marker():
    markup = use_table_keyboard(("art", "converse"), active="art")
    assert _callbacks(markup) == ["use:art", "use:converse"]
    texts = _buttons(markup)
    assert texts[0].startswith("\u2705")
    assert "art" in texts[0]
    assert texts[1] == "converse"


def test_use_table_keyboard_no_active():
    markup = use_table_keyboard(["art", "converse"])
    assert _callbacks(markup) == ["use:art", "use:converse"]
    assert _buttons(markup) == ["art", "converse"]


def test_sympathy_table_keyboard_callbacks():
    markup = sympathy_table_keyboard(["art", "converse"])
    assert _callbacks(markup) == ["sym:art", "sym:converse"]
    assert _buttons(markup) == ["art", "converse"]
