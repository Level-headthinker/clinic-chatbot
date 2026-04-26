# Reads everything from your .env file and makes it available to the whole app as a 
# single settings object. Every other file imports from here instead of reading .env directly.
from pydantic_settings import BaseSettings 


class Settings(BaseSettings):#creates a settings class that automatically reads from .env
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()