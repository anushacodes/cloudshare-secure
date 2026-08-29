"""Centralized application configuration settings."""

from __future__ import annotations

from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application runtime configuration settings."""

    AWS_REGION: str = Field(
        default_factory=lambda: os.getenv("AWS_REGION", "us-east-1")
    )
    AWS_ACCESS_KEY_ID: str | None = Field(
        default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID")
    )
    AWS_SECRET_ACCESS_KEY: str | None = Field(
        default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    AWS_SESSION_TOKEN: str | None = Field(
        default_factory=lambda: os.getenv("AWS_SESSION_TOKEN")
    )
    S3_BUCKET_NAME: str = Field(
        default_factory=lambda: os.getenv(
            "S3_BUCKET_NAME", "cloudshare-secure-bucket"
        )
    )
    DYNAMODB_TABLE_NAME: str = Field(
        default_factory=lambda: os.getenv("DYNAMODB_TABLE_NAME", "FileMetadata")
    )
    SES_SENDER_EMAIL: str = Field(
        default_factory=lambda: os.getenv(
            "SES_SENDER_EMAIL", "noreply@cloudshare.local"
        )
    )
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY")
        or "cloudshare-insecure-dev-secret-key-change-me"
    )
    APP_BASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "APP_BASE_URL", "http://localhost:8000"
        )
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

