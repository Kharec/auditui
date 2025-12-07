"""Authentication helpers for the Auditui app."""

from getpass import getpass
from pathlib import Path
from typing import Tuple

import audible

from .constants import AUTH_PATH


def authenticate(
    auth_path: Path = AUTH_PATH,
) -> Tuple[audible.Authenticator, audible.Client]:
    """Authenticate with Audible and return authenticator and client."""
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    if auth_path.exists():
        try:
            authenticator = audible.Authenticator.from_file(str(auth_path))
            audible_client = audible.Client(auth=authenticator)
            return authenticator, audible_client
        except (OSError, ValueError, KeyError) as exc:
            print(f"Failed to load existing auth: {exc}")
            print("Please re-authenticate.")

    print("Please authenticate with your Audible account.")

    email = input("\nEmail: ")
    password = getpass("Password: ")
    marketplace = input(
        "Marketplace locale (default: US): ").strip().upper() or "US"

    authenticator = audible.Authenticator.from_login(
        username=email, password=password, locale=marketplace
    )

    auth_path.parent.mkdir(parents=True, exist_ok=True)
    authenticator.to_file(str(auth_path))
    print("Authentication successful!")
    audible_client = audible.Client(auth=authenticator)
    return authenticator, audible_client
