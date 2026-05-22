"""Outbound messaging service.

WhatsApp  → Meta Cloud API (free 1,000 conversations/month)
SMS       → Twilio (optional — leave TWILIO_ACCOUNT_SID blank to disable)
Email     → SMTP via Gmail

All functions return True on success, False when the provider is not
configured, and raise RuntimeError on a delivery failure so callers
can log it as a failed delivery_status.
"""
import smtplib
from email.mime.text import MIMEText

import httpx

from app.config import settings

META_API_BASE = "https://graph.facebook.com/v19.0"


def _normalize_phone(phone: str) -> str:
    """Normalize Pakistani phone numbers to E.164 digits (no + prefix).

    Handles: 03001234567 → 923001234567 and +923001234567 → 923001234567
    """
    digits = phone.replace("+", "").replace(" ", "").replace("-", "")
    if digits.startswith("0") and len(digits) == 11:
        digits = "92" + digits[1:]
    return digits


# ── WhatsApp via Meta Cloud API ───────────────────────────────────────────────

def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp text message via Meta Cloud API.

    Returns True on success, False if Meta creds are not configured.
    Raises RuntimeError if the API call fails.
    """
    if not settings.META_PHONE_NUMBER_ID or not settings.META_ACCESS_TOKEN:
        return False

    to_number = _normalize_phone(to)
    url = f"{META_API_BASE}/{settings.META_PHONE_NUMBER_ID}/messages"

    resp = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": body},
        },
        timeout=10,
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Meta API error {resp.status_code}: {resp.text[:200]}"
        )
    return True


# ── SMS via Twilio (optional) ─────────────────────────────────────────────────

def send_sms(to: str, body: str) -> bool:
    """Send an SMS via Twilio.

    Returns False if Twilio is not configured (no error raised — SMS is
    treated as optional). Raises RuntimeError on a Twilio API failure.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return False
    if not settings.TWILIO_PHONE_NUMBER:
        return False

    try:
        from twilio.rest import Client
    except ImportError:
        raise RuntimeError("twilio package not installed. Run: pip install twilio")

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(body=body, from_=settings.TWILIO_PHONE_NUMBER, to=to)
    return True


# ── Email via SMTP ────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via Gmail SMTP.

    Returns False if email creds are not configured.
    Raises RuntimeError on SMTP failure.
    """
    if not settings.MAIL_EMAIL or not settings.MAIL_PASSWORD:
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_EMAIL
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.MAIL_EMAIL, settings.MAIL_PASSWORD)
        smtp.send_message(msg)
    return True
