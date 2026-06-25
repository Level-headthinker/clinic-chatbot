"""Gateway-agnostic payment layer.

A small ``PaymentProvider`` interface with two implementations:

  • ManualProvider  — test mode (no real money). Checkout returns a flag so the
    frontend can simulate a successful payment via a signed confirm call. Lets
    the whole subscription flow (trial → subscribe → active → cancel) be tested
    end-to-end with zero gateway setup.

  • SafepayProvider — Safepay (Pakistan): hosted checkout + HMAC-verified
    webhooks, recurring subscriptions in PKR. Fill the SAFEPAY_* env to use it.

Stripe is intentionally absent — it cannot pay out to Pakistani businesses.

Webhooks are the ONLY source of truth: a subscription is marked paid/active
solely from a signature-verified webhook event, never from the frontend.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import httpx

from app.config import settings
from app.services.plans import plan_price


class PaymentProvider:
    name = "base"

    def create_checkout(self, *, tenant_id: str, plan_key: str, checkout_ref: str,
                        customer_email: str, success_url: str, cancel_url: str) -> dict:
        """Return {"url": <hosted checkout url>} or {"manual": True, "ref": ...}."""
        raise NotImplementedError

    def verify_and_parse_webhook(self, raw: bytes, headers: dict) -> dict | None:
        """Return a normalized event dict or None if the signature is invalid.

        Normalized event:
          {"type": "paid"|"cancelled"|"failed", "checkout_ref": str,
           "subscription_id": str|None, "customer_id": str|None}
        """
        raise NotImplementedError


# ── Manual / test provider ──────────────────────────────────────────────────────

class ManualProvider(PaymentProvider):
    name = "manual"

    def create_checkout(self, *, tenant_id, plan_key, checkout_ref, customer_email,
                        success_url, cancel_url) -> dict:
        # No real gateway — the frontend shows a "Simulate payment" button that
        # calls /subscription/manual-confirm with this ref + the test secret.
        return {"manual": True, "ref": checkout_ref, "plan": plan_key}

    def verify_and_parse_webhook(self, raw, headers):
        # Manual mode has no external webhook.
        return None


# ── Safepay (Pakistan) ──────────────────────────────────────────────────────────

class SafepayProvider(PaymentProvider):
    name = "safepay"

    def _base(self) -> str:
        return ("https://sandbox.api.getsafepay.com"
                if settings.SAFEPAY_ENV != "production"
                else "https://api.getsafepay.com")

    def create_checkout(self, *, tenant_id, plan_key, checkout_ref, customer_email,
                        success_url, cancel_url) -> dict:
        if not settings.SAFEPAY_API_KEY:
            raise RuntimeError("SAFEPAY_API_KEY not configured")
        amount = plan_price(plan_key)
        # Create a payment session, then hand back the hosted checkout URL.
        # (Endpoint/shape per Safepay docs; adjust field names to your account.)
        resp = httpx.post(
            f"{self._base()}/order/v1/init",
            headers={"X-SFPY-MERCHANT-SECRET": settings.SAFEPAY_SECRET_KEY},
            json={
                "merchant_api_key": settings.SAFEPAY_API_KEY,
                "intent": "CYBERSOURCE",
                "mode": "payment",
                "currency": "PKR",
                "amount": amount * 100,           # minor units
                "metadata": {"tenant_id": str(tenant_id), "plan": plan_key,
                             "checkout_ref": checkout_ref},
            },
            timeout=20,
        )
        resp.raise_for_status()
        token = resp.json().get("data", {}).get("token", "")
        checkout_url = (
            f"{self._base().replace('api.', '')}/checkout/pay"
            f"?env={settings.SAFEPAY_ENV}&beacon={token}"
            f"&source=custom&order_id={checkout_ref}"
            f"&redirect_url={success_url}&cancel_url={cancel_url}"
        )
        return {"url": checkout_url, "token": token}

    def verify_and_parse_webhook(self, raw, headers):
        sig = headers.get("x-sfpy-signature") or headers.get("X-SFPY-Signature")
        if not settings.SAFEPAY_WEBHOOK_SECRET or not sig:
            return None
        expected = hmac.new(
            settings.SAFEPAY_WEBHOOK_SECRET.encode(), raw, hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        data = body.get("data", {})
        event = (body.get("type") or "").lower()
        meta = data.get("metadata", {}) or {}
        status_map = {
            "payment:created": "paid", "payment:succeeded": "paid",
            "subscription:cancelled": "cancelled", "payment:failed": "failed",
        }
        norm = status_map.get(event)
        if not norm:
            return None
        return {
            "type": norm,
            "checkout_ref": meta.get("checkout_ref") or data.get("order_id"),
            "subscription_id": data.get("subscription") or data.get("token"),
            "customer_id": data.get("customer"),
        }


_PROVIDERS = {"manual": ManualProvider, "safepay": SafepayProvider}


def get_provider() -> PaymentProvider:
    cls = _PROVIDERS.get(settings.PAYMENT_PROVIDER, ManualProvider)
    return cls()


def new_checkout_ref() -> str:
    return uuid.uuid4().hex
