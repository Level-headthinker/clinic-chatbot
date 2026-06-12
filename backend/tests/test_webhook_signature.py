"""
Test: WhatsApp webhook signature verification (X-Hub-Signature-256)
Ensures: forged webhook posts are rejected; genuine Meta-signed posts pass.
"""
import hashlib
import hmac

from app.config import settings
from app.routers.whatsapp import _verify_meta_signature

BODY = b'{"entry":[{"changes":[{"value":{"messages":[]}}]}]}'


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestWebhookSignature:
    def test_valid_signature_accepted(self, monkeypatch):
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        assert _verify_meta_signature(BODY, _sign(BODY, "test-secret")) is True

    def test_wrong_secret_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        assert _verify_meta_signature(BODY, _sign(BODY, "attacker-guess")) is False

    def test_missing_header_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        assert _verify_meta_signature(BODY, None) is False

    def test_malformed_header_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        assert _verify_meta_signature(BODY, "md5=abc123") is False

    def test_tampered_body_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        sig = _sign(BODY, "test-secret")
        assert _verify_meta_signature(BODY + b"x", sig) is False

    def test_no_secret_configured_skips_check(self, monkeypatch):
        # Dev-mode behavior: blank secret = check skipped (production boot
        # should set META_APP_SECRET; see PRODUCTION_CHECKLIST.md).
        monkeypatch.setattr(settings, "META_APP_SECRET", "")
        assert _verify_meta_signature(BODY, None) is True
