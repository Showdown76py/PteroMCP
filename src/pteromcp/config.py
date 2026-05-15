"""Settings for the PteroMCP server.

Configuration is loaded from environment variables (and optionally a `.env`
file). Every field is prefixed with `PTEROMCP_` to keep the namespace clean.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PanelType = Literal["auto", "pterodactyl", "pelican"]

ALL_CATEGORIES = {
    "users",
    "nodes",
    "servers",
    "eggs",
    "roles",
    "mounts",
    "databases",
    "allocations",
    "client",
}


class Settings(BaseSettings):
    """Runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="PTEROMCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    panel_url: HttpUrl = Field(
        description="Base URL of the Pterodactyl or Pelican panel (no trailing slash).",
    )
    application_key: str | None = Field(
        default=None,
        description="Admin API key for the /api/application/* surface.",
    )
    client_key: str | None = Field(
        default=None,
        description="User API key for the /api/client/* surface.",
    )
    panel_type: PanelType = Field(
        default="auto",
        description="Panel flavor. 'auto' will be detected from server responses.",
    )
    timeout: float = Field(default=30.0, gt=0, description="HTTP timeout in seconds.")
    read_only: bool = Field(
        default=False,
        description="When true, mutating tools refuse to run.",
    )
    disabled_categories: str = Field(
        default="",
        description="Comma-separated tool categories to disable.",
    )

    @field_validator("disabled_categories")
    @classmethod
    def _validate_categories(cls, value: str) -> str:
        if not value:
            return ""
        unknown = {c.strip() for c in value.split(",") if c.strip()} - ALL_CATEGORIES
        if unknown:
            raise ValueError(
                f"Unknown disabled categories: {sorted(unknown)}. Valid: {sorted(ALL_CATEGORIES)}"
            )
        return value

    def disabled_set(self) -> set[str]:
        return {c.strip() for c in self.disabled_categories.split(",") if c.strip()}

    def base_url(self) -> str:
        """Return the panel base URL without a trailing slash."""
        return str(self.panel_url).rstrip("/")

    def require_application_key(self) -> str:
        if not self.application_key:
            raise RuntimeError(
                "PTEROMCP_APPLICATION_KEY is required for this tool. "
                "Set it in your environment or .env file."
            )
        return self.application_key

    def require_client_key(self) -> str:
        if not self.client_key:
            raise RuntimeError(
                "PTEROMCP_CLIENT_KEY is required for client-surface tools. "
                "Set it in your environment or .env file."
            )
        return self.client_key
