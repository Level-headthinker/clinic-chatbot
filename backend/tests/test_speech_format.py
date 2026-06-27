"""
Test: voice-friendly date/time rendering.
The TTS voice reads zero-padded values ("09") and ISO dates oddly, so the voice
path must produce natural strings ("9 AM", "27 June 2026").
"""
from datetime import datetime

from app.services.conversation import format_slot, normalize_for_speech


class TestFormatSlot:
    def test_text_keeps_full_format(self):
        s = datetime(2026, 6, 9, 9, 0)
        assert format_slot(s) == "Tuesday, 09 June 2026 at 09:00 AM"

    def test_spoken_drops_padding_year_and_oclock(self):
        s = datetime(2026, 6, 9, 9, 0)
        assert format_slot(s, spoken=True) == "Tuesday, 9 June at 9 AM"

    def test_spoken_keeps_non_zero_minutes(self):
        s = datetime(2026, 6, 30, 14, 30)
        assert format_slot(s, spoken=True) == "Tuesday, 30 June at 2:30 PM"

    def test_spoken_midnight_and_noon(self):
        assert format_slot(datetime(2026, 6, 1, 0, 0), spoken=True).endswith("12 AM")
        assert format_slot(datetime(2026, 6, 1, 12, 0), spoken=True).endswith("12 PM")


class TestNormalizeForSpeech:
    def test_12h_oclock_becomes_bare_hour(self):
        assert normalize_for_speech("at 09:00 AM") == "at 9 AM"

    def test_12h_with_minutes_kept(self):
        assert normalize_for_speech("at 12:30 PM") == "at 12:30 PM"

    def test_iso_date_becomes_words(self):
        assert normalize_for_speech("on 2026-06-27") == "on 27 June 2026"

    def test_24h_leading_zero_stripped(self):
        assert normalize_for_speech("opens 09:30") == "opens 9:30"

    def test_plain_text_untouched(self):
        assert normalize_for_speech("Please call the clinic.") == "Please call the clinic."

    def test_empty(self):
        assert normalize_for_speech("") == ""
