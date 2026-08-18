import asyncio

from telegram import BotCommandScopeAllPrivateChats, BotCommandScopeChat

from datingbot.commands import ADMIN_COMMANDS, USER_COMMANDS, setup_commands

USER_EXPECTED = ["start", "profile", "browse", "cancel"]
ADMIN_EXPECTED = USER_EXPECTED + ["first", "dump", "reset", "help"]


def test_admin_commands_list():
    names = [c.command for c in ADMIN_COMMANDS]
    assert names == ADMIN_EXPECTED
    assert all(c.description for c in ADMIN_COMMANDS)


def test_user_commands_list():
    names = [c.command for c in USER_COMMANDS]
    assert names == USER_EXPECTED
    assert all(c.description for c in USER_COMMANDS)


class _FakeBot:
    def __init__(self):
        self.calls = []

    async def set_my_commands(self, commands, scope=None, **kwargs):
        self.calls.append((commands, scope))


def test_setup_commands_sets_user_menu_and_per_admin_menus():
    bot = _FakeBot()
    asyncio.run(setup_commands(bot, [111, 222]))
    assert len(bot.calls) == 3

    user_commands, user_scope = bot.calls[0]
    assert user_commands is USER_COMMANDS
    assert isinstance(user_scope, BotCommandScopeAllPrivateChats)

    admin_calls = bot.calls[1:]
    for commands, scope in admin_calls:
        assert commands is ADMIN_COMMANDS
        assert isinstance(scope, BotCommandScopeChat)
    assert {c[1].chat_id for c in admin_calls} == {111, 222}
