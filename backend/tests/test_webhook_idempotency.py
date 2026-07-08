"""
Integration test: WhatsApp webhook idempotency.

Meta redelivers a webhook if our 200 is slow. Without a de-dup check the brain
would run twice for one message → the patient gets a double reply, or worse, the
booking flow runs twice. The guard is ``dedup_seen`` (atomic check-and-mark),
surfaced to the router through ``_already_seen(message_id)``.

These tests exercise the in-memory dedup backend (no REDIS_URL), which is what a
single-worker deploy uses, and assert the router's own wrapper agrees. We clear
the module-level ``_seen`` store before each test so runs don't bleed into each
other.
"""
import pytest

from app.services import rate_limit
from app.services.rate_limit import dedup_seen
from app.routers.whatsapp import _already_seen


@pytest.fixture(autouse=True)
def clear_dedup_store():
    """Reset the in-memory de-dup store around every test in this module."""
    rate_limit._seen.clear()
    yield
    rate_limit._seen.clear()


class TestDedupSeen:
    def test_first_time_is_not_seen(self):
        assert dedup_seen("wa:msg:abc", 600) is False

    def test_second_time_is_seen(self):
        assert dedup_seen("wa:msg:abc", 600) is False   # first delivery
        assert dedup_seen("wa:msg:abc", 600) is True     # Meta's retry

    def test_distinct_messages_are_independent(self):
        assert dedup_seen("wa:msg:one", 600) is False
        assert dedup_seen("wa:msg:two", 600) is False    # different id, still first
        assert dedup_seen("wa:msg:one", 600) is True      # but one is now a repeat

    def test_expired_key_is_seen_again(self):
        # A zero/near-zero TTL means the mark lapses immediately, so a much later
        # redelivery is treated as new (acceptable — Meta retries within minutes).
        assert dedup_seen("wa:msg:ttl", 0) is False
        assert dedup_seen("wa:msg:ttl", 0) is False


class TestAlreadySeenWrapper:
    """The router calls _already_seen(msg_id); it must mirror dedup_seen and
    never treat a missing id as 'seen' (which would silently drop real messages)."""

    def test_blank_id_is_never_seen(self):
        assert _already_seen("") is False
        assert _already_seen("") is False   # still processes — no false-drop

    def test_repeat_delivery_is_flagged(self):
        mid = "wamid.HBgLOTIzMDA="
        assert _already_seen(mid) is False   # first webhook delivery → process
        assert _already_seen(mid) is True     # duplicate delivery → skip

    def test_two_different_ids_both_process(self):
        assert _already_seen("wamid.AAA") is False
        assert _already_seen("wamid.BBB") is False


class TestWebhookDedupDecision:
    """Simulate the router's per-message loop decision (whatsapp.py receive_webhook):
    only the FIRST delivery of a given id should be handed to _process_message."""

    def _messages_that_would_process(self, deliveries):
        processed = []
        for msg in deliveries:
            if msg.get("type") not in ("text", "audio"):
                continue
            if _already_seen(msg.get("id", "")):
                continue
            processed.append(msg["id"])
        return processed

    def test_duplicate_delivery_processed_once(self):
        payload = {"id": "wamid.DUP", "type": "text", "text": {"body": "book me"}}
        processed = self._messages_that_would_process([payload, payload, payload])
        assert processed == ["wamid.DUP"]   # 3 deliveries, processed exactly once

    def test_non_text_types_ignored(self):
        deliveries = [
            {"id": "wamid.IMG", "type": "image"},
            {"id": "wamid.TXT", "type": "text", "text": {"body": "hi"}},
            {"id": "wamid.AUD", "type": "audio"},
        ]
        processed = self._messages_that_would_process(deliveries)
        assert processed == ["wamid.TXT", "wamid.AUD"]  # image dropped, text+audio kept
