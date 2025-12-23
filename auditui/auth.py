"""Authentication helpers for the Auditui app."""

from pathlib import Path

import audible

from .constants import AUTH_PATH


def authenticate(
    auth_path: Path = AUTH_PATH,
) -> tuple[audible.Authenticator, audible.Client]:
    """Authenticate with Audible and return authenticator and client."""
    if not auth_path.exists():
        raise FileNotFoundError(
            "Authentication file not found. Please run 'auditui configure' to set up authentication.")

    try:
        authenticator = audible.Authenticator.from_file(str(auth_path))
        audible_client = audible.Client(auth=authenticator)
        return authenticator, audible_client
    except (OSError, ValueError, KeyError) as exc:
        raise ValueError(
            f"Failed to load existing authentication: {exc}") from exc
