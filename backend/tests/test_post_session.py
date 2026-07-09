"""
Post-treatment check-in (feature 4): one day after a completed appointment, the
bot messages the patient about recovery + medication — opt-in per clinic, and
never twice (post_session_sent flag).
"""
from datetime import datetime, timedelta

from conftest import needs_db  # noqa: E402

from app.models.appointment import Appointment
from app.services.reminder_agent import post_session_message, _post_session_checkins


class TestPostSessionMessage:
    def test_default_mentions_medication(self):
        msg = post_session_message("Ali", "Glow Clinic")
        assert "Ali" in msg and "Glow Clinic" in msg
        assert "medication" in msg.lower()

    def test_custom_placeholders_filled(self):
        msg = post_session_message("Sara", "Derma", custom="Hi {name}, {clinic} here — how's your skin?")
        assert msg == "Hi Sara, Derma here — how's your skin?"


def _completed_appt(t, b, d, phone, when, sent=False):
    return Appointment(
        tenant_id=t, branch_id=b, doctor_id=d, patient_name="P",
        patient_phone=phone, slot_datetime=when, status="completed",
        post_session_sent=sent,
    )


@needs_db
class TestPostSessionJob:
    def test_sends_once_when_enabled(self, db_session, make_clinic):
        from app.models.follow_up import FollowUp
        t, b, d = make_clinic("ps")
        t.post_session_enabled = True
        db_session.commit()
        yesterday = datetime.now() - timedelta(days=1)
        appt = _completed_appt(t.id, b.id, d.id, "0300000001", yesterday)
        db_session.add(appt)
        db_session.commit()

        res = _post_session_checkins(db_session, {})
        assert res["created"] == 1
        db_session.refresh(appt)
        assert appt.post_session_sent is True
        fu = db_session.query(FollowUp).filter(
            FollowUp.tenant_id == t.id, FollowUp.kind == "post_session").first()
        assert fu is not None

        # Running again does nothing (flag de-dups).
        res2 = _post_session_checkins(db_session, {})
        assert res2["created"] == 0

    def test_disabled_clinic_is_skipped(self, db_session, make_clinic):
        t, b, d = make_clinic("ps2")   # post_session_enabled defaults False
        db_session.commit()
        appt = _completed_appt(t.id, b.id, d.id, "0300000002",
                               datetime.now() - timedelta(days=1))
        db_session.add(appt)
        db_session.commit()
        res = _post_session_checkins(db_session, {})
        assert res["created"] == 0
        db_session.refresh(appt)
        assert appt.post_session_sent is False   # untouched

    def test_recent_and_old_visits_ignored(self, db_session, make_clinic):
        t, b, d = make_clinic("ps3")
        t.post_session_enabled = True
        db_session.commit()
        just_now = _completed_appt(t.id, b.id, d.id, "0300000003", datetime.now())
        long_ago = _completed_appt(t.id, b.id, d.id, "0300000004",
                                   datetime.now() - timedelta(days=10))
        db_session.add_all([just_now, long_ago])
        db_session.commit()
        res = _post_session_checkins(db_session, {})
        assert res["created"] == 0   # neither is ~1 day old
