"""Outbound messaging via Twilio (SMS + WhatsApp) and SMTP email.

All functions raise RuntimeError on failure so callers can catch and log.
If Twilio/email credentials are not configured, functions raise immediately
with a clear message — no silent failures.
"""
import smtplib
from email.mime.text import MIMEText
from app.config import settings


def _twilio_client():
    try:
        from twilio.rest import Client
    except ImportError:
        raise RuntimeError("twilio package not installed. Run: pip install twilio")
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(to: str, body: str) -> str:
    """Send an SMS via Twilio. Returns message SID."""
    if not settings.TWILIO_PHONE_NUMBER:
        raise RuntimeError("TWILIO_PHONE_NUMBER must be set in .env")
    client = _twilio_client()
    msg = client.messages.create(body=body, from_=settings.TWILIO_PHONE_NUMBER, to=to)
    return msg.sid


def send_whatsapp(to: str, body: str) -> str:
    """Send a WhatsApp message via Twilio. Returns message SID.

    `to` should be in the form '+923001234567' — the 'whatsapp:' prefix is added here.
    """
    if not settings.TWILIO_WHATSAPP_FROM:
        raise RuntimeError("TWILIO_WHATSAPP_FROM must be set in .env (e.g. +14155238886)")
    client = _twilio_client()
    from_wa = f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}"
    to_wa = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    msg = client.messages.create(body=body, from_=from_wa, to=to_wa)
    return msg.sid


def send_email(to: str, subject: str, body: str):
    """Send an email via SMTP (uses MAIL_EMAIL + MAIL_PASSWORD from config)."""
    if not settings.MAIL_EMAIL or not settings.MAIL_PASSWORD:
        raise RuntimeError("MAIL_EMAIL and MAIL_PASSWORD must be set in .env")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_EMAIL
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.MAIL_EMAIL, settings.MAIL_PASSWORD)
        smtp.send_message(msg)
