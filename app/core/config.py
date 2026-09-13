import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    # Application settings
    DEBUG: bool = False
    ENV: str = "development"

    # JWT settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 30

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_AUTH_REDIRECT_URI: str

    # Email settings - correct field names for FastAPI-Mail 1.4.2
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str = "noreply@example.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.example.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_SUPPRESS_SEND: bool = False  # Set to True in test environment
    FRONTEND_URL: str = "http://localhost:5173"  # URL for the frontend app

    # MQTT / EMQX. Compose sets MQTT_ROLE=api|simulator; that copies the
    # matching MQTT_API_* / MQTT_SIM_* pair onto MQTT_USERNAME/PASSWORD.
    MQTT_HOST: str = "emqx"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    MQTT_BASE_TOPIC: str = "snrub"
    MQTT_ROLE: str | None = None
    MQTT_API_USERNAME: str | None = None
    MQTT_API_PASSWORD: str | None = None
    MQTT_SIM_USERNAME: str | None = None
    MQTT_SIM_PASSWORD: str | None = None

    # Identity that owns auto-emitted incident reports (Phase 4 incident_emitter).
    # Seeded by an Alembic data migration; the emitter looks it up by email.
    SYSTEM_USER_EMAIL: str = "system@snrub.io"

    @model_validator(mode="after")
    def _apply_mqtt_role_credentials(self) -> "Settings":
        role = (self.MQTT_ROLE or "").strip().lower()
        if role == "api" and self.MQTT_API_PASSWORD:
            self.MQTT_USERNAME = self.MQTT_API_USERNAME or "snrub_api"
            self.MQTT_PASSWORD = self.MQTT_API_PASSWORD
        elif role == "simulator" and self.MQTT_SIM_PASSWORD:
            self.MQTT_USERNAME = self.MQTT_SIM_USERNAME or "snrub_sim"
            self.MQTT_PASSWORD = self.MQTT_SIM_PASSWORD
        return self

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'development')}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        """Construct database URL"""
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
