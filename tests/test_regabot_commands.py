import asyncio

from telegram import BotCommandScopeChat

from regabot.commands import ADMIN_COMMANDS, setup_admin_menu

EXPECTED = ["use", "first", "second", "third", "love", "love_force", "reset", "help"]


def test_admin_commands_list():
    names = [c.command for c in ADMIN_COMMANDS]
    assert names == EXPECTED
    assert all(c.description for c in ADMIN_COMMANDS)


class _FakeBot:
    def __init__(self):
        self.calls = []

    async def set_my_commands(self, commands, scope=None, **kwargs):
        self.calls.append((commands, scope))


def test_setup_admin_menu_calls_per_admin():
    bot = _FakeBot()
    sent = asyncio.run(setup_admin_menu(bot, [111, 222]))
    assert sent == 2
    assert len(bot.calls) == 2
    for commands, scope in bot.calls:
        assert commands is ADMIN_COMMANDS
        assert isinstance(scope, BotCommandScopeChat)
    assert {c[1].chat_id for c in bot.calls} == {111, 222}


def test_setup_admin_menu_empty():
    assert asyncio.run(setup_admin_menu(_FakeBot(), [])) == 0
