"""Configuration helpers for the Auditui app."""

from getpass import getpass
from pathlib import Path

import audible

from .constants import AUTH_PATH


def configure(
    auth_path: Path = AUTH_PATH,
) -> tuple[audible.Authenticator, audible.Client]:
    """Force re-authentication and save credentials."""
    if auth_path.exists():
        response = input(
            "Configuration already exists. Are you sure you want to overwrite it? (y/N): "
        ).strip().lower()
        if response not in ("yes", "y"):
            print("Configuration cancelled.")
            raise SystemExit(0)

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
