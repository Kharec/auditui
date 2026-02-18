"""Aggregates listening time, account info, and subscription data for display."""

from datetime import date
from typing import Any

from ..types import LibraryItem

from . import account as account_mod
from . import email as email_mod
from . import format as format_mod
from . import listening as listening_mod


class StatsAggregator:
    """Builds a list of (label, value) stats from the API, auth, and library."""

    def __init__(
        self,
        client: Any,
        auth: Any,
        library_client: Any,
        all_items: list[LibraryItem],
    ) -> None:
        self.client = client
        self.auth = auth
        self.library_client = library_client
        self.all_items = all_items

    def get_stats(self, today: date | None = None) -> list[tuple[str, str]]:
        if not self.client:
            return []
        today = today or date.today()
        signup_year = listening_mod.get_signup_year(self.client)
        month_time = listening_mod.get_listening_time(
            self.client, 1, today.strftime("%Y-%m")
        )
        year_time = listening_mod.get_listening_time(
            self.client, 12, today.strftime("%Y-01")
        )
        finished_count = listening_mod.get_finished_books_count(
            self.library_client, self.all_items or []
        )
        total_books = len(self.all_items) if self.all_items else 0
        email = email_mod.resolve_email(
            self.auth,
            self.client,
            get_account_info=lambda: account_mod.get_account_info(self.client),
        )
        country = account_mod.get_country(self.auth)
        subscription_name = "Unknown"
        subscription_price = "Unknown"
        next_bill_date = "Unknown"
        account_info = account_mod.get_account_info(self.client)
        if account_info:
            subscription_data = account_mod.get_subscription_details(
                account_info)
            if subscription_data:
                if name := subscription_data.get("name"):
                    subscription_name = name
                if bill_date := subscription_data.get("next_bill_date"):
                    next_bill_date = format_mod.format_date(bill_date)
                if bill_amount := subscription_data.get("next_bill_amount", {}):
                    amount = bill_amount.get("currency_value")
                    currency = bill_amount.get("currency_code", "EUR")
                    if amount is not None:
                        subscription_price = f"{amount} {currency}"
        stats_items = []
        if email != "Unknown":
            stats_items.append(("Email", email))
        stats_items.append(("Country Store", country))
        stats_items.append(
            ("Signup Year", str(signup_year) if signup_year > 0 else "Unknown")
        )
        if next_bill_date != "Unknown":
            stats_items.append(("Next Credit", next_bill_date))
            stats_items.append(("Next Bill", next_bill_date))
        if subscription_name != "Unknown":
            stats_items.append(("Subscription", subscription_name))
        if subscription_price != "Unknown":
            stats_items.append(("Price", subscription_price))
        stats_items.append(("This Month", format_mod.format_time(month_time)))
        stats_items.append(("This Year", format_mod.format_time(year_time)))
        stats_items.append(
            ("Books Finished", f"{finished_count} / {total_books}"))
        return stats_items
