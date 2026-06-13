"""
Test: booking confirmation matching + language continuity
Ensures:
  1. "I want to book an appointment" is INTENT, not confirmation — the old
     substring matcher treated it as "yes" and instantly booked the top slot.
  2. Word-boundary matching — "ok" must not fire inside "looking"/"booked".
  3. A digit-only message (phone number) keeps the conversation's language
     instead of flipping an Urdu chat to English.
"""
from app.services.conversation import is_confirmation_message
from app.services.llm import detect_language


class TestConfirmation:
    def test_booking_request_is_not_confirmation(self):
        assert is_confirmation_message("I want to book an appointment") is False
        assert is_confirmation_message("book me with the dentist") is False

    def test_substring_false_positives_gone(self):
        assert is_confirmation_message("I am looking for a dermatologist") is False
        assert is_confirmation_message("is my appointment booked?") is False

    def test_plain_yes_confirms(self):
        assert is_confirmation_message("yes") is True
        assert is_confirmation_message("Yes please") is True
        assert is_confirmation_message("ok") is True
        assert is_confirmation_message("confirm") is True

    def test_negated_confirm_does_not_book(self):
        # The manual-test failure: "not just confirm…" booked an appointment.
        assert is_confirmation_message("not just confirm and tell me which treatment she book") is False
        assert is_confirmation_message("don't confirm anything yet") is False
        assert is_confirmation_message("no, not yet") is False
        assert is_confirmation_message("nahi abhi confirm mat karo") is False

    def test_roman_urdu_confirmations(self):
        assert is_confirmation_message("haan") is True
        assert is_confirmation_message("ji bilkul") is True
        assert is_confirmation_message("theek hai") is True
        assert is_confirmation_message("kar do") is True

    def test_empty_message_safe(self):
        assert is_confirmation_message("") is False
        assert is_confirmation_message(None) is False


class TestLanguageContinuity:
    def test_digits_keep_previous_language(self):
        assert detect_language("03001234567", fallback="ur-roman") == "ur-roman"
        assert detect_language("03001234567", fallback="ur") == "ur"

    def test_digits_default_english_without_history(self):
        assert detect_language("03001234567") == "en"

    def test_invalid_fallback_sanitized(self):
        assert detect_language("12345", fallback="klingon") == "en"

    def test_real_text_still_detected(self):
        assert detect_language("mujhe appointment chahiye", fallback="en") == "ur-roman"
        assert detect_language("I want an appointment", fallback="ur") == "en"
