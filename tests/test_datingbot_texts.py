from __future__ import annotations

from datingbot import texts
from datingbot.constants import GENDER_F, GENDER_M, LOOKING_F, LOOKING_M
from datingbot.keyboards import (
    browse_keyboard,
    match_keyboard,
    profile_keyboard,
    refresh_keyboard,
    registration_nav_keyboard,
    swipe_keyboard,
    verification_keyboard,
)
from datingbot.models import Profile


def _buttons(markup):
    return [btn.text for row in markup.inline_keyboard for btn in row]


def _callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


def test_swipe_keyboard_callbacks():
    markup = swipe_keyboard(42)
    assert _callbacks(markup) == ["swipe:pass:42", "swipe:like:42", "swipe:stop"]


def test_swipe_keyboard_two_rows_labeled():
    markup = swipe_keyboard(42)
    rows = [[btn.text for btn in row] for row in markup.inline_keyboard]
    assert rows[0] == ["×  ДАЛЬШЕ", "♥  НРАВИТСЯ"]
    assert rows[1] == ["ПАУЗА"]


def test_browse_keyboard_callback():
    assert _callbacks(browse_keyboard()) == ["browse:start"]


def test_refresh_keyboard_callback():
    assert _callbacks(refresh_keyboard()) == ["browse:start"]


def test_profile_keyboard_adapts_to_verification():
    assert _callbacks(profile_keyboard(False)) == ["profile:edit"]
    assert _callbacks(profile_keyboard(True)) == ["browse:start", "profile:edit"]


def test_registration_navigation():
    assert _callbacks(registration_nav_keyboard()) == ["reg:cancel"]
    assert _callbacks(registration_nav_keyboard("gender")) == [
        "reg:back:gender",
        "reg:cancel",
    ]


def test_match_keyboard_with_username():
    markup = match_keyboard("alice")
    button = markup.inline_keyboard[0][0]
    assert button.url == "https://t.me/alice"
    assert "@alice" in button.text


def test_match_keyboard_without_username():
    assert match_keyboard(None) is None


def test_verification_keyboard_callbacks():
    markup = verification_keyboard(42)
    assert _callbacks(markup) == ["verify:ok:42", "verify:no:42"]


def _p(uid: int, gender: str, looking: str, username: str | None) -> Profile:
    return Profile(
        user_id=uid,
        chat_id=uid,
        name=f"u{uid}",
        username=username,
        gender=gender,
        age=25,
        looking_for=looking,
        hobbies="hobby",
        dream="dream",
    )


def test_match_message_with_username():
    partner = _p(2, GENDER_F, LOOKING_M, "alice")
    msg = texts.match_message(partner)
    assert "@alice" in msg
    assert "https://t.me/alice" in msg
    assert "Телефон" not in msg


def test_match_message_without_username_warns():
    partner = _p(2, GENDER_F, LOOKING_M, None)
    msg = texts.match_message(partner)
    assert "@username не указан" in msg
    assert "обратись к организаторам" in msg


def test_swipe_card_has_no_contact_info():
    p = _p(2, GENDER_F, LOOKING_M, "alice")
    card = texts.swipe_card(p)
    assert "alice" not in card
    assert "Telegram" not in card


def test_profile_saved_no_phone():
    p = _p(1, GENDER_M, LOOKING_F, None)
    assert "Телефон" not in texts.profile_saved(p)


def test_profile_saved_mentions_verification():
    p = _p(1, GENDER_M, LOOKING_F, None)
    assert "провер" in texts.profile_saved(p).lower()


def test_admin_verification_card_has_contact_and_uid():
    p = _p(2, GENDER_F, LOOKING_M, "alice")
    card = texts.admin_verification_card(p)
    assert "@alice" in card
    assert "uid: 2" in card


def test_admin_verdict_card_shows_admin_and_verdict():
    p = _p(2, GENDER_F, LOOKING_M, "alice")
    approved = texts.admin_verdict_card(p, True, "@boss (uid=9)")
    rejected = texts.admin_verdict_card(p, False, "@boss (uid=9)")
    assert "Одобрена" in approved and "✅" in approved and "@boss (uid=9)" in approved
    assert "Отклонена" in rejected and "❌" in rejected and "@boss (uid=9)" in rejected


def test_photo_is_required():
    assert "обязательно" in texts.ASK_PHOTO
    assert "Пропустить" not in texts.ASK_PHOTO
    assert "Пропустить" not in texts.PHOTO_INVALID


# --- HTML-форматирование ---
def _evil_p() -> Profile:
    return Profile(
        user_id=3,
        chat_id=3,
        name="<b>Аня</b> & Co",
        username="eve<i>",
        gender=GENDER_F,
        age=25,
        looking_for=LOOKING_M,
        hobbies="<script>hack</script>",
        dream="мечта & счастье",
    )


def test_swipe_card_escapes_user_input():
    card = texts.swipe_card(_evil_p())
    assert "<script>" not in card
    assert "<b>Аня</b>" not in card
    assert "&lt;script&gt;hack&lt;/script&gt;" in card
    assert "мечта &amp; счастье" in card


def test_match_message_escapes_user_input():
    msg = texts.match_message(_evil_p())
    assert "<script>" not in msg
    assert "<i>" not in msg
    assert "@eve&lt;i&gt;" in msg


def test_admin_cards_escape_user_input():
    p = _evil_p()
    for card in (
        texts.admin_verification_card(p),
        texts.admin_verdict_card(p, True, "@boss (uid=9)"),
    ):
        assert "<script>" not in card
        assert "<b>Аня</b>" not in card


def test_swipe_card_header_has_name_and_age():
    card = texts.swipe_card(_p(2, GENDER_F, LOOKING_M, "alice"))
    assert "<b>U2 · 25</b>" in card
    assert "ХОББИ" in card
    assert "МЕЧТА" in card


def test_registration_prompts_have_step_counters():
    assert "Шаг 1/7" in texts.start_open(False)
    assert "Шаг 2/7" in texts.ASK_GENDER
    assert "Шаг 3/7" in texts.ASK_AGE
    assert "Шаг 4/7" in texts.ASK_LOOKING_FOR
    assert "Шаг 5/7" in texts.ASK_PHOTO
    assert "Шаг 6/7" in texts.ASK_HOBBIES
    assert "Шаг 7/7" in texts.ASK_DREAM


def test_maximum_profile_still_fits_photo_caption():
    p = _p(2, GENDER_F, LOOKING_M, "alice")
    p.name = "N" * 40
    p.hobbies = "H" * 240
    p.dream = "D" * 240
    assert len(texts.swipe_card(p)) < 1024
    assert len(texts.profile_saved(p)) < 1024


def test_profile_overview_shows_status():
    assert "НА ПРОВЕРКЕ" in texts.profile_overview(_p(1, GENDER_M, LOOKING_F, None))
