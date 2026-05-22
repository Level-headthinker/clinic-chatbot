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
    MAIL_EMAIL: str = ""
    MAIL_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Twilio — SMS, WhatsApp, Voice
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""        # E.164 e.g. +12025551234
    TWILIO_WHATSAPP_FROM: str = ""       # WhatsApp sender e.g. +14155238886
    VOICE_BRANCH_SLUG: str = ""          # Branch slug the voice agent answers for

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
