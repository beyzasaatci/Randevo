from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Barber Appointment API"
    environment: str = "development"
    database_url: str
    frontend_origin: str = "http://localhost:3000"
    secret_key: str
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    business_timezone: str = "Europe/Istanbul"
    slot_interval_minutes: int = 30
    admin_username: str = "admin"
    admin_password: str = "change-me-in-env"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()