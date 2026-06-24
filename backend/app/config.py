"""
Application Configuration
---------------------------
Centralised settings management using environment variables.
All configuration is read from .env or environment vars, with
sensible defaults for local development.

Usage:
    from app.config import settings
    print(settings.JWT_SECRET)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    """Immutable application settings, loaded once at import time."""

    # ── Database ──────────────────────────────────────────────────────
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME: str = os.getenv("DB_NAME", "cloud_kitchen")
    DB_TIMEOUT_MS: int = int(os.getenv("DB_TIMEOUT_MS", "5000"))

    # ── JWT / Auth ────────────────────────────────────────────────────
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        "cloud-kitchen-secret-key-change-in-production-please-change",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    JWT_REFRESH_EXPIRY_DAYS: int = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "7"))

    # ── CORS ──────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

    # ── Application ───────────────────────────────────────────────────
    APP_NAME: str = "Cloud Kitchen API"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── Rate Limiting (future) ────────────────────────────────────────
    RATE_LIMIT_DEFAULT: int = int(os.getenv("RATE_LIMIT_DEFAULT", "100"))  # per minute
    RATE_LIMIT_AUTH: int = int(os.getenv("RATE_LIMIT_AUTH", "20"))  # per minute

    # ── Branch defaults ───────────────────────────────────────────────
    DEFAULT_SERVICE_RADIUS_KM: float = float(os.getenv("DEFAULT_SERVICE_RADIUS_KM", "15.0"))

    # ── Super Admin bootstrap ─────────────────────────────────────────
    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", "")
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", "")


settings = Settings()
