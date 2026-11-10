"""Errors raised by the client."""

from __future__ import annotations

from typing import Any


class ZenonWalletError(Exception):
    """Base class for every error raised by this package."""


class ConfigurationError(ZenonWalletError):
    """A required setting (URL, credentials, wallet password) is missing or invalid."""


class ConnectionFailed(ZenonWalletError):
    """The Wallet API could not be reached or did not answer in time."""


class ApiError(ZenonWalletError):
    """The Wallet API answered with an HTTP error status.

    The API reports problems as RFC 7807 "problem details". ``title`` and
    ``detail`` come from that body when it is present; ``errors`` holds the
    per-field validation messages of a 422 response.
    """

    def __init__(
        self,
        status: int,
        title: str = "",
        detail: str = "",
        errors: dict[str, Any] | None = None,
        body: Any = None,
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.errors = errors or {}
        self.body = body
        message = f"HTTP {status}"
        description = detail or title
        if description:
            message += f": {description}"
        if self.errors:
            fields = "; ".join(
                f"{field}: {', '.join(map(str, messages)) if isinstance(messages, list) else messages}"
                for field, messages in self.errors.items()
            )
            message += f" ({fields})"
        super().__init__(message)


class AuthenticationError(ApiError):
    """The username or password was rejected, or the account lacks the required role."""


class PlasmaTimeout(ZenonWalletError):
    """An address did not get plasma within the allowed time."""
