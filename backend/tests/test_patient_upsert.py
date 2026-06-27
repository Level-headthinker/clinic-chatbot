"""
Test: returning-patient name matching used by upsert_patient_for_booking.
Same person (case/spacing/word-order tolerant) → reuse; clearly different name
→ new entry. This is what decides reuse-vs-new when one number books again.
"""
from app.services.conversation import _name_matches


class TestNameMatches:
    def test_identical(self):
        assert _name_matches("Ali Khan", "Ali Khan") is True

    def test_case_and_spacing_insensitive(self):
        assert _name_matches("ALI  khan", "ali khan") is True

    def test_word_order(self):
        # Same person, words reordered.
        assert _name_matches("Ali Khan", "Khan Ali") is True

    def test_minor_typo_still_matches(self):
        assert _name_matches("Ayesha Siddiqui", "Ayesha Sidiqui") is True

    def test_different_people_dont_match(self):
        assert _name_matches("Ali", "Ahmed") is False
        assert _name_matches("Ali Khan", "Sara Malik") is False

    def test_empty_never_matches(self):
        assert _name_matches("", "Ali") is False
        assert _name_matches("Ali", "") is False
