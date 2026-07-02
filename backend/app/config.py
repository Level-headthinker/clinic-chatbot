# Reads everything from your .env file and makes it available to the whole app as a 
# single settings object. Every other file imports from here instead of reading .env directly.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str

    # Deployment environment label (development | staging | production).
    ENVIRONMENT: str = "development"
    # Error monitoring (Sentry). Blank = disabled — set the DSN to turn it on.
    SENTRY_DSN: str = ""
    # Redis URL for rate-limit + webhook de-dup across workers. Blank = in-memory
    # fallback (fine for a single worker; required before running >1 worker).
    REDIS_URL: str = ""
    MAIL_EMAIL: str = ""
    MAIL_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Twilio — SMS only (optional, keep blank to disable)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""        # E.164 e.g. +12025551234

    # Meta Cloud API — WhatsApp (free 1,000 conversations/month)
    META_PHONE_NUMBER_ID: str = ""       # From Meta App Dashboard
    META_ACCESS_TOKEN: str = ""          # Permanent system user token
    META_VERIFY_TOKEN: str = "clinicbot_verify"  # Any secret string for webhook verification
    # App Secret (Meta → App → Settings → Basic). When set, every incoming
    # webhook POST is HMAC-verified (X-Hub-Signature-256). REQUIRED in production.
    META_APP_SECRET: str = ""

    # Shared secret VAPI must send (X-Vapi-Secret header) to reach the
    # /voice/vapi-server and /voice/vapi-llm endpoints. Blank = endpoints closed.
    VAPI_SERVER_SECRET: str = ""

    # ── Automated reminders (the "follow-up agent") ────────────
    # A daily job messages patients before their next visit and nudges leads who
    # enquired but never booked — turning follow-ups into automatic outreach.
    AUTO_REMINDERS_ENABLED: bool = True
    NEXT_VISIT_REMINDER_DAYS_BEFORE: int = 1   # remind this many days before a next-visit date
    LEAD_NUDGE_AFTER_DAYS: int = 2             # nudge an un-booked lead this many days after it came in
    LEAD_NUDGE_MAX_AGE_DAYS: int = 30         # don't nudge leads older than this (avoid spamming history)

    # WhatsApp message templates (pre-approved in Meta) — required to deliver
    # reminders OUTSIDE the 24-hour window. Set each to your approved template's
    # name; blank = fall back to free-form text (only delivers within 24h).
    # See app/services/WHATSAPP_TEMPLATES.md for the expected body/parameters.
    WA_TEMPLATE_LANG: str = "en"               # language code of your templates (e.g. en, en_US)
    WA_TEMPLATE_NEXT_VISIT: str = ""           # params: {{1}} name {{2}} clinic {{3}} doctor {{4}} date
    WA_TEMPLATE_LEAD_NUDGE: str = ""           # params: {{1}} name {{2}} clinic
    WA_TEMPLATE_APPT_REMINDER: str = ""        # params: {{1}} name {{2}} clinic {{3}} doctor {{4}} datetime

    # ── Billing / subscriptions ────────────────────────────────
    # Public base URL of the frontend (for checkout success/cancel redirects).
    APP_BASE_URL: str = "http://localhost:3000"
    # Which payment gateway to use: "manual" (test mode — no real money) or "safepay".
    PAYMENT_PROVIDER: str = "manual"
    # Safepay (Pakistan). Get these from the Safepay dashboard. Sandbox first.
    SAFEPAY_API_KEY: str = ""
    SAFEPAY_SECRET_KEY: str = ""
    SAFEPAY_WEBHOOK_SECRET: str = ""
    SAFEPAY_ENV: str = "sandbox"          # sandbox | production

    # VAPI.ai — Voice Agent (free 10 min/month, then pay-per-minute)
    VAPI_API_KEY: str = ""               # From vapi.ai dashboard
    VAPI_PHONE_NUMBER_ID: str = ""       # VAPI phone number ID (not the number itself)
    VOICE_BRANCH_SLUG: str = ""          # Branch slug the voice agent answers for

    # VIS — Voice Intelligence Service (self-hosted STT/TTS; replaces VAPI cost)
    VIS_API_URL: str = ""                # e.g. http://localhost:8080 or your deployed VIS
    VIS_API_KEY: str = ""                # must match VIS's API_KEY (blank if VIS is open)
    # Which languages reply to a WhatsApp voice note with a VOICE note (others reply text).
    # Default "en"; once VIS has ElevenLabs configured for Urdu use "en,ur,ur-roman".
    WHATSAPP_VOICE_LANGS: str = "en"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def whatsapp_voice_langs(self) -> set[str]:
        return {x.strip() for x in self.WHATSAPP_VOICE_LANGS.split(",") if x.strip()}


settings = Settings()
