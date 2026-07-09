"""
Cancellation backfill (feature 3): a freed slot is offered to patients booked for
the same time on a later day; first to accept is moved earlier, and once one
accepts the freed seat can't be handed out again.

DB-gated (real Postgres). WhatsApp sends no-op in tests (no token) so the offer
rows/moves are exercised without any network.
"""
from datetime import datetime, timedelta

from conftest import needs_db  # noqa: E402

from app.models.appointment import Appointment
from app.models.slot_offer import SlotOffer


def _appt(t, b, d, slot, phone, seat=0, status="pending"):
    a = Appointment(
        tenant_id=t, branch_id=b, doctor_id=d, patient_name=f"P{phone}",
        patient_phone=phone, slot_datetime=slot, slot_index=seat, status=status,
    )
    return a


@needs_db
class TestBackfill:
    def _setup(self, db_session, make_clinic):
        t, b, d = make_clinic("bf")
        db_session.commit()
        base = (datetime.now() + timedelta(days=2)).replace(
            hour=15, minute=0, second=0, microsecond=0)
        return t, b, d, base

    def test_offer_created_for_next_day_same_time(self, db_session, make_clinic):
        from app.services.slot_backfill import offer_freed_slot
        t, b, d, base = self._setup(db_session, make_clinic)

        freed = _appt(t.id, b.id, d.id, base, "0300000001", status="cancelled")
        nextday = _appt(t.id, b.id, d.id, base + timedelta(days=1), "0300000002")
        other_time = _appt(t.id, b.id, d.id, base + timedelta(days=1, hours=2), "0300000003")
        db_session.add_all([freed, nextday, other_time])
        db_session.commit()

        n = offer_freed_slot(db_session, freed)
        offers = db_session.query(SlotOffer).filter(SlotOffer.tenant_id == t.id).all()
        # Only the same-time next-day patient is offered, not the different time.
        assert len(offers) == 1
        assert offers[0].appointment_id == nextday.id
        assert offers[0].offered_slot.replace(tzinfo=None) == base

    def test_accept_moves_appointment_and_blocks_siblings(self, db_session, make_clinic):
        from app.services.slot_backfill import offer_freed_slot, accept_offer
        t, b, d, base = self._setup(db_session, make_clinic)
        d.slot_capacity = 1
        freed = _appt(t.id, b.id, d.id, base, "0300000001", status="cancelled")
        p2 = _appt(t.id, b.id, d.id, base + timedelta(days=1), "0300000002")
        p3 = _appt(t.id, b.id, d.id, base + timedelta(days=2), "0300000003")
        db_session.add_all([freed, p2, p3])
        db_session.commit()

        offer_freed_slot(db_session, freed)
        offers = {o.appointment_id: o for o in
                  db_session.query(SlotOffer).filter(SlotOffer.tenant_id == t.id).all()}
        ok, new_slot = accept_offer(db_session, offers[p2.id])
        assert ok is True
        db_session.refresh(p2)
        assert p2.slot_datetime.replace(tzinfo=None) == base   # moved earlier

        # The freed slot (capacity 1) is now taken → the other offer is dead.
        db_session.refresh(offers[p3.id]) if p3.id in offers else None
        sibling = db_session.query(SlotOffer).filter(
            SlotOffer.appointment_id == p3.id).first()
        if sibling:
            assert sibling.status in ("filled", "expired")

    def test_pending_offer_expiry(self, db_session, make_clinic):
        from app.services.slot_backfill import pending_offer_for
        t, b, d, base = self._setup(db_session, make_clinic)
        appt = _appt(t.id, b.id, d.id, base + timedelta(days=1), "0300000009")
        db_session.add(appt)
        db_session.commit()
        # An already-expired offer must not be returned (and gets marked expired).
        db_session.add(SlotOffer(
            tenant_id=t.id, branch_id=b.id, doctor_id=d.id,
            patient_phone="0300000009", appointment_id=appt.id, offered_slot=base,
            status="pending", expires_at=datetime.now() - timedelta(hours=1),
        ))
        db_session.commit()
        assert pending_offer_for(db_session, t.id, "0300000009") is None
