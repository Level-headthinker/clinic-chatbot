"""
Integration test: the double-booking guard.

Two patients grabbing the SAME doctor + SAME slot at the same instant must not
both get an appointment. The guard is the partial unique index
``uq_active_appointment_slot`` on (tenant_id, doctor_id, slot_datetime) WHERE
status IN ('pending','confirmed'). This index only exists on Postgres, so these
tests are gated on TEST_DATABASE_URL — SQLite would silently accept the duplicate
and give a false green.

The index (not the app-level pre-check) is what actually holds under a race:
two requests can both pass the "is this slot free?" read, but only one INSERT can
win the unique index — the loser gets IntegrityError, which the booking routers
translate into "This slot is already booked".
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from conftest import needs_db  # noqa: E402

from app.models.appointment import Appointment


def _make_appt(tenant_id, branch_id, doctor_id, slot, phone="03001112223",
               status="pending"):
    return Appointment(
        tenant_id=tenant_id,
        branch_id=branch_id,
        doctor_id=doctor_id,
        patient_name="Race Patient",
        patient_phone=phone,
        slot_datetime=slot,
        status=status,
    )


@needs_db
class TestDoubleBookingGuard:
    def test_second_booking_for_same_slot_is_rejected(self, db_session, make_clinic):
        """The core race: same tenant/doctor/slot booked twice → second fails."""
        t, b, d = make_clinic("clinic-a")
        slot = datetime.now() + timedelta(days=2)

        db_session.add(_make_appt(t.id, b.id, d.id, slot, phone="03000000001"))
        db_session.commit()

        # Second patient, same slot — the unique index must reject this.
        db_session.add(_make_appt(t.id, b.id, d.id, slot, phone="03000000002"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

        # Exactly one booking survived.
        rows = db_session.query(Appointment).filter(
            Appointment.tenant_id == t.id,
            Appointment.doctor_id == d.id,
            Appointment.slot_datetime == slot,
        ).all()
        assert len(rows) == 1
        assert rows[0].patient_phone == "03000000001"

    def test_concurrent_bookings_only_one_wins(self, make_clinic, db_session):
        """Two *separate* DB connections commit the same slot back-to-back
        (simulating two workers). One commits, the other hits the index."""
        t, b, d = make_clinic("clinic-race")
        db_session.commit()  # make the clinic visible to the other connection
        slot = datetime.now() + timedelta(days=3)

        url = db_session.get_bind().url
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        s1, s2 = Session(), Session()
        try:
            s1.add(_make_appt(t.id, b.id, d.id, slot, phone="03000000011"))
            s2.add(_make_appt(t.id, b.id, d.id, slot, phone="03000000012"))

            s1.commit()  # first worker wins
            with pytest.raises(IntegrityError):
                s2.commit()  # second worker loses to the unique index
            s2.rollback()

            winners = s1.query(Appointment).filter(
                Appointment.tenant_id == t.id,
                Appointment.slot_datetime == slot,
            ).all()
            assert len(winners) == 1
        finally:
            s1.close(); s2.close(); engine.dispose()

    def test_different_doctors_same_slot_both_allowed(self, db_session, make_clinic):
        """The guard is scoped to a doctor — two doctors can hold the same time."""
        t, b, d1 = make_clinic("clinic-b")
        from app.models.doctor import Doctor
        d2 = Doctor(tenant_id=t.id, branch_id=b.id, name="Dr Two", specialty="GP")
        db_session.add(d2); db_session.flush()
        slot = datetime.now() + timedelta(days=2)

        db_session.add(_make_appt(t.id, b.id, d1.id, slot, phone="03000000021"))
        db_session.add(_make_appt(t.id, b.id, d2.id, slot, phone="03000000022"))
        db_session.commit()  # must NOT raise

        rows = db_session.query(Appointment).filter(
            Appointment.tenant_id == t.id, Appointment.slot_datetime == slot
        ).all()
        assert len(rows) == 2

    def test_different_tenants_same_slot_both_allowed(self, db_session, make_clinic):
        """Two unrelated clinics can each book the same wall-clock time."""
        ta, ba, da = make_clinic("clinic-x")
        tb, bb, dbn = make_clinic("clinic-y")
        slot = datetime.now() + timedelta(days=2)

        db_session.add(_make_appt(ta.id, ba.id, da.id, slot, phone="03000000031"))
        db_session.add(_make_appt(tb.id, bb.id, dbn.id, slot, phone="03000000032"))
        db_session.commit()  # different tenants → different index rows

        assert db_session.query(Appointment).filter(
            Appointment.slot_datetime == slot
        ).count() == 2

    def test_cancelled_slot_can_be_rebooked(self, db_session, make_clinic):
        """The index is PARTIAL (only pending/confirmed). Once an appointment is
        cancelled it leaves the index, so the freed slot can be booked again."""
        t, b, d = make_clinic("clinic-c")
        slot = datetime.now() + timedelta(days=2)

        first = _make_appt(t.id, b.id, d.id, slot, phone="03000000041")
        db_session.add(first)
        db_session.commit()

        # Cancel it — now it no longer occupies the partial index.
        first.status = "cancelled"
        db_session.commit()

        db_session.add(_make_appt(t.id, b.id, d.id, slot, phone="03000000042"))
        db_session.commit()  # must succeed — slot is free again

        active = db_session.query(Appointment).filter(
            Appointment.tenant_id == t.id,
            Appointment.slot_datetime == slot,
            Appointment.status.in_(["pending", "confirmed"]),
        ).all()
        assert len(active) == 1
        assert active[0].patient_phone == "03000000042"
