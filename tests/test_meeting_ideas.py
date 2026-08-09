from config import MEETING_IDEAS, _load_meeting_ideas
from regabot.models import Participant
from regabot.texts import love_message


def _p(badge: int, uid: int, name: str = "A", username: str | None = None) -> Participant:
    return Participant(
        chat_id=uid,
        user_id=uid,
        name=name,
        phone="+0",
        username=username,
        table_tag="art",
        badge=badge,
    )


def test_parser_blocks_and_bullets(tmp_path):
    f = tmp_path / "ideas.txt"
    f.write_text(
        "# comment\n"
        "\n"
        "[converse]\n"
        "- idea one\n"
        "- idea two\n"
        "\n"
        "[art]\n"
        "- gallery\n",
        encoding="utf-8",
    )
    result = _load_meeting_ideas(str(f))
    assert result == {"converse": ["idea one", "idea two"], "art": ["gallery"]}


def test_parser_missing_file(tmp_path):
    assert _load_meeting_ideas(str(tmp_path / "nope.txt")) == {}


def test_shipped_file_has_known_tables():
    # файл из репозитория должен содержать оба стола по умолчанию
    assert set(MEETING_IDEAS.keys()) >= {"converse", "art"}
    assert all(MEETING_IDEAS[t] for t in ("converse", "art"))


def test_love_message_renders_ideas_list():
    me = _p(1, 1, "A")
    other = _p(2, 2, "B", username="bb")
    regs = {1: me, 2: other}
    msg = love_message(me, [(2, True)], regs, ["coffee", "gallery"])
    assert "Идеи для первой встречи:" in msg
    assert "- coffee" in msg
    assert "- gallery" in msg
    assert "[СуперМэтч]" in msg


def test_love_message_empty_ideas_fallback():
    me = _p(1, 1, "A")
    other = _p(2, 2, "B")
    regs = {1: me, 2: other}
    msg = love_message(me, [(2, False)], regs, [])
    assert "Хорошей первой встречи" in msg
