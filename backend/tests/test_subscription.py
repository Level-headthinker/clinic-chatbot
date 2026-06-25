"""
Test: subscription access logic + webhook security.
Pure-logic tests (no DB) on the access rules, plus the gateway webhook
signature check — the security-critical parts.
"""
from datetime import datetime, timedelta, timezone

from app.services import subscription_service as s
from app.services.payments import ManualProvider, SafepayProvider
from app.config import settings


def _now():
    return datetime.now(timezone.utc)


class _Sub:
    """Minimal stand-in for the Subscription model (attributes only)."""
    def __init__(self, **kw):
        self.status = kw.get("status", "trialing")
        self.plan = kw.get("plan", "starter")
        self.trial_ends_at = kw.get("trial_ends_at")
        self.current_period_end = kw.get("current_period_end")
        self.cancel_at_period_end = kw.get("cancel_at_period_end", False)
        self.gateway = kw.get("gateway")


class TestAccessRules:
    def test_trial_within_window_has_access(self):
        sub = _Sub(status="trialing", trial_ends_at=_now() + timedelta(days=2))
        assert s.has_access(sub) is True
        assert s.effective_status(sub) == "trialing"

    def test_trial_expired_no_access(self):
        sub = _Sub(status="trialing", trial_ends_at=_now() - timedelta(hours=1))
        assert s.has_access(sub) is False
        assert s.effective_status(sub) == "expired"

    def test_active_within_period_has_access(self):
        sub = _Sub(status="active", current_period_end=_now() + timedelta(days=10))
        assert s.has_access(sub) is True

    def test_active_period_ended_reads_expired(self):
        sub = _Sub(status="active", current_period_end=_now() - timedelta(days=1))
        assert s.has_access(sub) is False
        assert s.effective_status(sub) == "expired"

    def test_cancel_anytime_keeps_access_until_period_end(self):
        # The key "cancel anytime" promise: still entitled until the paid period ends.
        sub = _Sub(status="cancelled", cancel_at_period_end=True,
                   current_period_end=_now() + timedelta(days=5))
        assert s.has_access(sub) is True

    def test_cancelled_after_period_no_access(self):
        sub = _Sub(status="cancelled", current_period_end=_now() - timedelta(days=1))
        assert s.has_access(sub) is False


class TestStatusPayload:
    def test_trial_payload(self):
        sub = _Sub(status="trialing", plan="growth", trial_ends_at=_now() + timedelta(days=3))
        p = s.status_payload(sub)
        assert p["is_trial"] is True and p["has_access"] is True
        assert p["plan"] == "growth" and p["days_left"] in (2, 3)


class TestWebhookSecurity:
    def test_manual_provider_has_no_webhook(self):
        assert ManualProvider().verify_and_parse_webhook(b"{}", {}) is None

    def test_safepay_rejects_bad_signature(self, monkeypatch):
        monkeypatch.setattr(settings, "SAFEPAY_WEBHOOK_SECRET", "whsec")
        prov = SafepayProvider()
        assert prov.verify_and_parse_webhook(b'{"type":"payment:succeeded"}', {"x-sfpy-signature": "wrong"}) is None

    def test_safepay_rejects_missing_secret(self, monkeypatch):
        monkeypatch.setattr(settings, "SAFEPAY_WEBHOOK_SECRET", "")
        prov = SafepayProvider()
        assert prov.verify_and_parse_webhook(b'{}', {"x-sfpy-signature": "x"}) is None
