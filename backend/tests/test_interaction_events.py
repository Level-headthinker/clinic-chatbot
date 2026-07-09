"""
Tests for the data feedback loop's capture + learn layers.

- classify_outcome is a pure function → tested without a DB.
- log_interaction / summarize touch real tables → gated on TEST_DATABASE_URL
  (Postgres, via the shared db_session + make_clinic fixtures in conftest).

A standing guarantee we assert here: the event row carries NO patient PII — only
derived signals — so the feedback loop is safe to aggregate on healthcare data.
"""
from conftest import needs_db  # noqa: E402

from app.services.conversation_logger import classify_outcome


class TestClassifyOutcome:
    def test_booked_wins_over_everything(self):
        assert classify_outcome(
            booked=True, lead_captured=True, slots_offered=True
        ) == "booked"

    def test_lead_beats_slots(self):
        assert classify_outcome(
            booked=False, lead_captured=True, slots_offered=True
        ) == "lead_captured"

    def test_slots_offered(self):
        assert classify_outcome(
            booked=False, lead_captured=False, slots_offered=True
        ) == "slots_offered"

    def test_default_is_answered(self):
        assert classify_outcome(
            booked=False, lead_captured=False, slots_offered=False
        ) == "answered"


@needs_db
class TestLogInteraction:
    def test_row_is_written_with_no_pii(self, db_session, make_clinic):
        from app.models.interaction_event import InteractionEvent
        from app.services.conversation_logger import log_interaction

        t, b, d = make_clinic("clinic-fb")
        db_session.commit()

        log_interaction(
            db_session,
            tenant_id=t.id, branch_id=b.id, session_token="wa:0300",
            modality="text", intent="book_appointment", language="en",
            outcome="booked", is_returning=True, visit_count=3,
            kb_hit=True, output_flagged=False, has_contact=True,
        )

        row = db_session.query(InteractionEvent).filter(
            InteractionEvent.tenant_id == t.id
        ).one()
        assert row.outcome == "booked"
        assert row.intent == "book_appointment"
        assert row.visit_count == 3
        # PHI-safety: the model has no column that could hold a name/phone/text.
        cols = set(InteractionEvent.__table__.columns.keys())
        for forbidden in ("patient_name", "patient_phone", "message", "text", "body"):
            assert forbidden not in cols

    def test_logging_never_raises_on_bad_input(self, db_session, make_clinic):
        from app.services.conversation_logger import log_interaction
        t, b, d = make_clinic("clinic-fb2")
        db_session.commit()
        # visit_count None / weird types must be coerced, not crash the chat.
        log_interaction(
            db_session, tenant_id=t.id, branch_id=b.id,
            outcome="answered", visit_count=None,
        )  # must not raise


@needs_db
class TestSummarize:
    def test_conversion_and_weak_spots(self, db_session, make_clinic):
        from app.services.conversation_logger import log_interaction
        from app.services.interaction_analytics import summarize

        t, b, d = make_clinic("clinic-sum")
        db_session.commit()

        # 3 booking-intent turns: 1 booked, 1 slots-only, 1 answered-with-KB-miss.
        log_interaction(db_session, tenant_id=t.id, branch_id=b.id,
                        intent="book_appointment", outcome="booked", kb_hit=True)
        log_interaction(db_session, tenant_id=t.id, branch_id=b.id,
                        intent="book_appointment", outcome="slots_offered", kb_hit=True)
        log_interaction(db_session, tenant_id=t.id, branch_id=b.id,
                        intent="book_appointment", outcome="answered", kb_hit=False)
        # 1 general turn where the output guard fired.
        log_interaction(db_session, tenant_id=t.id, branch_id=b.id,
                        intent="general", outcome="answered",
                        kb_hit=False, output_flagged=True)

        s = summarize(db_session, t.id, days=30)
        assert s["total_turns"] == 4
        assert s["booking_intent_turns"] == 3
        assert s["booked"] == 1
        assert s["conversion_rate"] == round(1 / 3, 3)   # 1 booked of 3 who tried
        assert s["kb_miss_rate"] == round(2 / 4, 3)        # 2 of 4 turns had no KB answer
        assert s["output_flag_rate"] == round(1 / 4, 3)
        assert s["intents"]["book_appointment"] == 3

    def test_empty_tenant_is_zeroed_not_error(self, db_session, make_clinic):
        from app.services.interaction_analytics import summarize
        t, b, d = make_clinic("clinic-empty")
        db_session.commit()
        s = summarize(db_session, t.id, days=30)
        assert s["total_turns"] == 0
        assert s["conversion_rate"] == 0.0
