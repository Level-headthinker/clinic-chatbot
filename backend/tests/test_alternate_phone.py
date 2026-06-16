"""
Test: alternate booking number capture.
- Same number as primary (any format) → no alternate (saved once).
- A different number typed for the booking → captured as alternate.
"""
from app.services.conversation import detect_alternate_phone, _last10, _format_pk_phone


class TestLast10:
    def test_formats_collapse_to_same_identity(self):
        assert _last10("923001234567") == "3001234567"
        assert _last10("03001234567") == "3001234567"
        assert _last10("+92 300 1234567") == "3001234567"

    def test_format_pk_phone(self):
        assert _format_pk_phone("923121234567") == "03121234567"
        assert _format_pk_phone("+92 312 1234567") == "03121234567"


class TestAlternateDetection:
    def test_same_number_no_alternate(self):
        # Patient messaging from 923001234567 types their own number back.
        assert detect_alternate_phone("923001234567", "my number is 03001234567") is None

    def test_different_number_is_captured(self):
        alt = detect_alternate_phone("923001234567", "book for my mother, her number is 03121234567")
        assert alt == "03121234567"

    def test_no_phone_in_message(self):
        assert detect_alternate_phone("923001234567", "I'd like a hydra facial please") is None

    def test_no_primary_yet(self):
        # Web chat before any number is known → nothing to compare against.
        assert detect_alternate_phone("", "0300 123 4567") is None

    def test_whatsapp_format_primary_vs_local_typed_same(self):
        # WA sends 92-form; patient types 0-form of the SAME number → no alt.
        assert detect_alternate_phone("923009990005", "0300 999 0005") is None
