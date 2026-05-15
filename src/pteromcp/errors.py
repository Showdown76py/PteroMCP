"""Domain-specific error types for PteroMCP."""

from __future__ import annotations

from typing import Any


class PteroError(RuntimeError):
    """Base class for all PteroMCP runtime errors."""


class PanelHTTPError(PteroError):
    """An HTTP error returned by the panel API."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        method: str,
        url: str,
        payload: Any = None,
    ) -> None:
        self.status_code = status_code
        self.method = method
        self.url = url
        self.payload = payload
        super().__init__(f"{method} {url} -> {status_code}: {message}")


class ReadOnlyError(PteroError):
    """Raised when a mutating call is attempted while in read-only mode."""

    def __init__(self, method: str, path: str) -> None:
        super().__init__(
            f"Refusing {method} {path}: PteroMCP is configured in read-only mode."
        )


class MissingCredentialError(PteroError):
    """Raised when a required API key is not configured."""
