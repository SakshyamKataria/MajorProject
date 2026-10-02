from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Google Gemini
    GEMINI_API_KEY: str = ""

    # Hugging Face (PyAnnote Diarization)
    HUGGINGFACE_TOKEN: str = ""

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_ENDPOINT_URL: str = ""

    # Whisper STT
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Google Calendar OAuth
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_REDIRECT_URI: str = "http://localhost:8000/calendar/callback"
    GOOGLE_CALENDAR_SCOPE: str = "https://www.googleapis.com/auth/calendar.events"
    FRONTEND_URL: str = "http://localhost:5173"
    DEFAULT_USER_ID: str = "9828d241-1733-4fcf-a305-75663e9af362"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
