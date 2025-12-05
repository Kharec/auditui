#!/usr/bin/env python3
"""Stats playground for Audible TUI - get your listening stats"""

import logging
from getpass import getpass
from pathlib import Path

import audible


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("audible").setLevel(logging.WARNING)


class AudibleStats:
    """Class to handle Audible authentication and stats retrieval."""

    def __init__(self) -> None:
        """Initialize the stats handler with authentication."""
        self.auth: audible.Authenticator | None = None
        self.client: audible.Client | None = None
        self.home = Path.home()

    def authenticate(self) -> None:
        """Authenticate with Audible and store auth and client."""
        auth_path = self.home / ".config" / "auditui" / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)

        if auth_path.exists():
            try:
                self.auth = audible.Authenticator.from_file(str(auth_path))
                self.client = audible.Client(auth=self.auth)
                return
            except Exception:
                logger.info("Failed to load existing auth. Re-authenticating.\n")

        email = input("Email: ")
        password = getpass("Password: ")
        marketplace = (
            input("Marketplace locale (default: US): ").strip().upper() or "US"
        )

        self.auth = audible.Authenticator.from_login(
            username=email, password=password, locale=marketplace
        )
        self.auth.to_file(str(auth_path))
        self.client = audible.Client(auth=self.auth)


def main() -> None:
    """Main entry point."""
    worker = AudibleStats()
    worker.authenticate()
    worker.print_stats()  # TBD


if __name__ == "__main__":
    main()
