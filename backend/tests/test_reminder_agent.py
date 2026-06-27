"""
Test: automatic reminder agent message building + helpers.
Messages must be personal (name, clinic, date) and the doctor label must be
normalised. Delivery/DB selection is integration-level and not covered here.
"""
from app.services import reminder_agent as ra


class TestNextVisitMessage:
    def test_includes_key_details(self):
        m = ra.next_visit_message("Ali", "City Clinic", "Dr. Sara", "Monday, 30 June", "skin review")
        assert "Ali" in m
        assert "City Clinic" in m
        assert "Dr. Sara" in m
        assert "30 June" in m
        assert "skin review" in m

    def test_works_without_doctor_or_reason(self):
        m = ra.next_visit_message("Ali", "City Clinic", None, "Monday, 30 June", None)
        assert "Ali" in m and "30 June" in m
        assert "with" not in m.split("\n")[2]  # no dangling "with" when no doctor


class TestLeadNudge:
    def test_includes_name_and_clinic(self):
        m = ra.lead_nudge_message("Ayesha", "City Clinic")
        assert "Ayesha" in m and "City Clinic" in m


class TestDoctorLabel:
    def test_prefixes_dr_when_missing(self):
        assert ra._doctor_label("Sara") == "Dr. Sara"

    def test_keeps_existing_dr(self):
        assert ra._doctor_label("Dr. Khan") == "Dr. Khan"
        assert ra._doctor_label("dr. khan") == "dr. khan"

    def test_none_stays_none(self):
        assert ra._doctor_label(None) is None
