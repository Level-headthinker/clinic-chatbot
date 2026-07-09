"""
Per-doctor slot capacity (features 1 & 2).

Pure tests for capacity_of; DB-gated tests for seat-claiming, the capacity-aware
anti-double-book index, and that a full slot is skipped so the next opening is
offered.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from conftest import needs_db  # noqa: E402

from app.models.appointment import Appointment
from app.services.slot_capacity import (
    capacity_of, next_free_seat, seats_taken, slot_has_room,
)


class TestCapacityOf:
    def test_default_is_one(self):
        class D:  # a doctor with no slot_capacity attribute
            pass
        assert capacity_of(D()) == 1

    def test_respects_value(self):
        class D:
            slot_capacity = 3
        assert capacity_of(D()) == 3

    def test_clamps_zero_and_none_to_one(self):
        class Z:
            slot_capacity = 0
        class N:
            slot_capacity = None
        assert capacity_of(Z()) == 1
        assert capacity_of(N()) == 1


def _appt(t, b, d, slot, seat, phone, status="pending"):
    return Appointment(
        tenant_id=t, branch_id=b, doctor_id=d, patient_name="P",
        patient_phone=phone, slot_datetime=slot, slot_index=seat, status=status,
    )


@needs_db
class TestSeatClaiming:
    def test_capacity_two_fills_then_full(self, db_session, make_clinic):
        t, b, d = make_clinic("cap")
        d.slot_capacity = 2
        db_session.commit()
        slot = datetime.now() + timedelta(days=2)

        assert next_free_seat(db_session, d, t.id, slot) == 0
        db_session.add(_appt(t.id, b.id, d.id, slot, 0, "0300000001"))
        db_session.commit()

        assert seats_taken(db_session, t.id, d.id, slot) == 1
        assert next_free_seat(db_session, d, t.id, slot) == 1
        db_session.add(_appt(t.id, b.id, d.id, slot, 1, "0300000002"))
        db_session.commit()

        assert next_free_seat(db_session, d, t.id, slot) is None   # full
        assert slot_has_room(db_session, d, t.id, slot) is False

    def test_reusing_a_seat_is_rejected_by_index(self, db_session, make_clinic):
        t, b, d = make_clinic("cap2")
        d.slot_capacity = 2
        db_session.commit()
        slot = datetime.now() + timedelta(days=2)
        db_session.add(_appt(t.id, b.id, d.id, slot, 0, "1"))
        db_session.add(_appt(t.id, b.id, d.id, slot, 1, "2"))
        db_session.commit()

        # Two patients racing for the same seat index → the unique index wins.
        db_session.add(_appt(t.id, b.id, d.id, slot, 1, "3"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_cancelled_booking_frees_a_seat(self, db_session, make_clinic):
        t, b, d = make_clinic("cap3")
        d.slot_capacity = 1
        db_session.commit()
        slot = datetime.now() + timedelta(days=2)
        a = _appt(t.id, b.id, d.id, slot, 0, "1")
        db_session.add(a)
        db_session.commit()
        assert next_free_seat(db_session, d, t.id, slot) is None

        a.status = "cancelled"
        db_session.commit()
        assert next_free_seat(db_session, d, t.id, slot) == 0   # freed


@needs_db
class TestGenerateSlotsSkipsFull:
    def test_full_slot_is_skipped_next_opening_offered(self, db_session, make_clinic):
        from app.services.conversation import generate_doctor_slots
        t, b, d = make_clinic("slots")
        # Offer 09:00–11:00 every day so the window always has slots.
        d.slot_capacity = 1
        d.timings = [
            {"day": day, "from": "9:00 AM", "to": "11:00 AM"}
            for day in ["monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday"]
        ]
        db_session.commit()

        first = generate_doctor_slots(d, t.id, db_session, max_slots=1)[0]
        # Fill that first slot to capacity.
        db_session.add(_appt(t.id, b.id, d.id, first, 0, "0300000009"))
        db_session.commit()

        after = generate_doctor_slots(d, t.id, db_session, max_slots=1)[0]
        assert after > first   # the full slot is gone; next opening is offered
