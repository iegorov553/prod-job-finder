"""Authorization helpers for API routes."""

from __future__ import annotations

from typing import Optional

from job_finder.resources import api_messages


class AuthorizationError(ValueError):
    """Raised when API auth fails."""


def require_bearer_token(authorization: Optional[str], expected_token: str) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthorizationError(api_messages.UNAUTHORIZED)
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != expected_token:
        raise AuthorizationError(api_messages.UNAUTHORIZED)
