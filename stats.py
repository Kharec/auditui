#!/usr/bin/env python3
"""Stats playground for Audible TUI - get your listening stats"""

import logging
from datetime import date
from getpass import getpass
from pathlib import Path

import audible


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("audible").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


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

    def get_signup_year(self) -> int:
        """Get signup year by checking activity in each month, each year."""
        current_year = date.today().year
        start_year = 1995

        try:
            stats = self.client.get(
                "1.0/stats/aggregates",
                monthly_listening_interval_duration="12",
                monthly_listening_interval_start_date=f"{current_year}-01",
                store="Audible",
            )
            monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
            if not monthly_stats or not any(
                stat.get("aggregated_sum", 0) > 0 for stat in monthly_stats
            ):
                logger.warning("Could not determine signup year")
                return 0
        except Exception:
            logger.warning("Could not determine signup year")
            return 0

        left, right = start_year, current_year
        earliest_year = current_year

        while left <= right:
            middle = (left + right) // 2
            try:
                stats = self.client.get(
                    "1.0/stats/aggregates",
                    monthly_listening_interval_duration="12",
                    monthly_listening_interval_start_date=f"{middle}-01",
                    store="Audible",
                )
                monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
                has_activity = bool(
                    monthly_stats
                    and any(stat.get("aggregated_sum", 0) > 0 for stat in monthly_stats)
                )
            except Exception:
                has_activity = False

            if has_activity:
                earliest_year = middle
                right = middle - 1
            else:
                left = middle + 1

        return earliest_year


def main() -> None:
    """Main entry point."""
    worker = AudibleStats()
    worker.authenticate()
    print(worker.get_signup_year())


if __name__ == "__main__":
    main()
