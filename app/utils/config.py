import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    openweather_api_key: str | None
    google_places_api_key: str | None
    google_oauth_client_id: str | None
    google_oauth_allowed_client_ids: list[str]
    frontend_origins: list[str]
    database_url: str
    session_expiry_days: int
    default_city: str
    default_latitude: float
    default_longitude: float
    google_calendar_id: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    frontend_origins = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash"),
        openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),
        google_places_api_key=os.getenv("GOOGLE_PLACES_API_KEY"),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_allowed_client_ids=[
            value.strip()
            for value in os.getenv("GOOGLE_OAUTH_ALLOWED_CLIENT_IDS", os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")).split(",")
            if value.strip()
        ],
        frontend_origins=frontend_origins,
        database_url=os.getenv("DATABASE_URL", "sqlite:///./planner.db"),
        session_expiry_days=int(os.getenv("SESSION_EXPIRY_DAYS", "30")),
        default_city=os.getenv("DEFAULT_CITY", "Mumbai"),
        default_latitude=float(os.getenv("DEFAULT_LATITUDE", "19.0330")),
        default_longitude=float(os.getenv("DEFAULT_LONGITUDE", "73.0297")),
        google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
    )
