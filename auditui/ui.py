"""UI components for the Auditui application."""

import json
from datetime import date, datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from .constants import CONFIG_PATH


KEY_DISPLAY_MAP = {
    "ctrl+": "^",
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
    "space": "Space",
    "enter": "Enter",
}

KEY_COLOR = "#f9e2af"
DESC_COLOR = "#cdd6f4"


class HelpScreen(ModalScreen):
    """Help screen displaying all available keybindings."""

    BINDINGS = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    @staticmethod
    def _format_key_display(key: str) -> str:
        """Format a key string for display with symbols."""
        result = key
        for old, new in KEY_DISPLAY_MAP.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def _parse_binding(binding: tuple | object) -> tuple[str, str]:
        """Extract key and description from a binding."""
        if isinstance(binding, tuple):
            return binding[0], binding[2]
        return binding.key, binding.description

    def _make_item(self, binding: tuple | object) -> ListItem:
        """Create a ListItem for a single binding."""
        key, description = self._parse_binding(binding)
        key_display = self._format_key_display(key)
        text = f"[bold {KEY_COLOR}]{key_display:>12}[/]  [{DESC_COLOR}]{description}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        bindings = list(self.app.BINDINGS)
        mid = (len(bindings) + 1) // 2

        with Container(id="help_container"):
            yield Static("Key Bindings", id="help_title")
            with Horizontal(id="help_content"):
                yield ListView(
                    *[self._make_item(b) for b in bindings[:mid]],
                    classes="help_list",
                )
                yield ListView(
                    *[self._make_item(b) for b in bindings[mid:]],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]?[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    def action_dismiss(self) -> None:
        self.dismiss()


class StatsScreen(ModalScreen):
    """Stats screen displaying listening statistics."""

    BINDINGS = [("escape", "dismiss", "Close"), ("s", "dismiss", "Close")]

    def _format_time(self, milliseconds: int) -> str:
        """Format milliseconds as hours and minutes."""
        total_seconds = int(milliseconds) // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h{minutes:02d}"
        return f"{minutes}m"

    def _format_date(self, date_str: str | None) -> str:
        """Format ISO date string for display."""
        if not date_str:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return date_str

    def _get_signup_year(self) -> int:
        """Get signup year using binary search on listening activity."""
        if not self.app.client:
            return 0

        current_year = date.today().year

        try:
            stats = self.app.client.get(
                "1.0/stats/aggregates",
                monthly_listening_interval_duration="12",
                monthly_listening_interval_start_date=f"{current_year}-01",
                store="Audible",
            )
            if not self._has_activity(stats):
                return 0
        except Exception:
            return 0

        left, right = 1995, current_year
        earliest_year = current_year

        while left <= right:
            middle = (left + right) // 2
            try:
                stats = self.app.client.get(
                    "1.0/stats/aggregates",
                    monthly_listening_interval_duration="12",
                    monthly_listening_interval_start_date=f"{middle}-01",
                    store="Audible",
                )
                has_activity = self._has_activity(stats)
            except Exception:
                has_activity = False

            if has_activity:
                earliest_year = middle
                right = middle - 1
            else:
                left = middle + 1

        return earliest_year

    @staticmethod
    def _has_activity(stats: dict) -> bool:
        """Check if stats contain any listening activity."""
        monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
        return bool(
            monthly_stats and any(s.get("aggregated_sum", 0)
                                  > 0 for s in monthly_stats)
        )

    def _get_listening_time(self, duration: int, start_date: str) -> int:
        """Get listening time in milliseconds for a given period."""
        if not self.app.client:
            return 0

        try:
            stats = self.app.client.get(
                "1.0/stats/aggregates",
                monthly_listening_interval_duration=str(duration),
                monthly_listening_interval_start_date=start_date,
                store="Audible",
            )
            monthly_stats = stats.get("aggregated_monthly_listening_stats", [])
            return sum(s.get("aggregated_sum", 0) for s in monthly_stats)
        except Exception:
            return 0

    def _get_finished_books_count(self) -> int:
        """Get count of finished books from library."""
        if not self.app.library_client or not self.app.all_items:
            return 0
        return sum(
            1 for item in self.app.all_items if self.app.library_client.is_finished(item)
        )

    def _get_account_info(self) -> dict:
        """Get account information including subscription details."""
        if not self.app.client:
            return {}

        account_info = {}
        endpoints = [
            (
                "1.0/account/information",
                "subscription_details,plan_summary,subscription_details_payment_instrument,delinquency_status,customer_benefits,customer_segments,directed_ids",
            ),
            (
                "1.0/customer/information",
                "subscription_details_premium,subscription_details_rodizio,customer_segment,subscription_details_channels,migration_details",
            ),
            (
                "1.0/customer/status",
                "benefits_status,member_giving_status,prime_benefits_status,prospect_benefits_status",
            ),
        ]

        for endpoint, response_groups in endpoints:
            try:
                response = self.app.client.get(
                    endpoint, response_groups=response_groups)
                account_info.update(response)
            except Exception:
                pass

        return account_info

    def _get_email(self) -> str:
        """Get email from config file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("email", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def _get_subscription_details(self, account_info: dict) -> dict:
        """Extract subscription details from nested API response."""
        paths = [
            ["customer_details", "subscription", "subscription_details"],
            ["customer", "customer_details", "subscription", "subscription_details"],
            ["subscription_details"],
            ["subscription", "subscription_details"],
        ]
        for path in paths:
            data = account_info
            for key in path:
                if isinstance(data, dict):
                    data = data.get(key)
                else:
                    break
            if isinstance(data, list) and data:
                return data[0]
        return {}

    def _get_country(self) -> str:
        """Get country from authenticator locale."""
        if not self.app.auth:
            return "Unknown"

        try:
            locale_obj = getattr(self.app.auth, "locale", None)
            if not locale_obj:
                return "Unknown"

            if hasattr(locale_obj, "country_code"):
                return locale_obj.country_code.upper()
            if hasattr(locale_obj, "domain"):
                return locale_obj.domain.upper()
            if isinstance(locale_obj, str):
                return locale_obj.split("_")[-1].upper() if "_" in locale_obj else locale_obj.upper()
            return str(locale_obj)
        except Exception:
            return "Unknown"

    def _make_stat_item(self, label: str, value: str) -> ListItem:
        """Create a ListItem for a stat."""
        text = f"[bold {KEY_COLOR}]{label:>16}[/]  [{DESC_COLOR}]{value:<25}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        if not self.app.client:
            with Container(id="help_container"):
                yield Static("Statistics", id="help_title")
                yield Static(
                    "Not authenticated. Please restart and authenticate.",
                    classes="help_row",
                )
                yield Static(
                    f"Press [bold {KEY_COLOR}]s[/] or [bold {KEY_COLOR}]Escape[/] to close",
                    id="help_footer",
                )
            return

        today = date.today()
        stats_items = self._build_stats_items(today)

        with Container(id="help_container"):
            yield Static("Statistics", id="help_title")
            with Vertical(id="help_content"):
                yield ListView(
                    *[self._make_stat_item(label, value)
                      for label, value in stats_items],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]s[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    def _build_stats_items(self, today: date) -> list[tuple[str, str]]:
        """Build the list of stats items to display."""
        signup_year = self._get_signup_year()
        month_time = self._get_listening_time(1, today.strftime("%Y-%m"))
        year_time = self._get_listening_time(12, today.strftime("%Y-01"))
        finished_count = self._get_finished_books_count()
        total_books = len(self.app.all_items) if self.app.all_items else 0

        email = self._get_email()
        country = self._get_country()

        subscription_name = "Unknown"
        subscription_price = "Unknown"
        next_bill_date = "Unknown"

        account_info = self._get_account_info()
        if account_info:
            subscription_data = self._get_subscription_details(account_info)
            if subscription_data:
                if name := subscription_data.get("name"):
                    subscription_name = name

                if bill_date := subscription_data.get("next_bill_date"):
                    next_bill_date = self._format_date(bill_date)

                if bill_amount := subscription_data.get("next_bill_amount", {}):
                    amount = bill_amount.get("currency_value")
                    currency = bill_amount.get("currency_code", "EUR")
                    if amount is not None:
                        subscription_price = f"{amount} {currency}"

        stats_items = []
        if email != "Unknown":
            stats_items.append(("Email", email))
        stats_items.append(("Country Store", country))
        stats_items.append(("Signup Year", str(signup_year)
                           if signup_year > 0 else "Unknown"))
        if next_bill_date != "Unknown":
            stats_items.append(("Next Credit", next_bill_date))
            stats_items.append(("Next Bill", next_bill_date))
        if subscription_name != "Unknown":
            stats_items.append(("Subscription", subscription_name))
        if subscription_price != "Unknown":
            stats_items.append(("Price", subscription_price))
        stats_items.append(("This Month", self._format_time(month_time)))
        stats_items.append(("This Year", self._format_time(year_time)))
        stats_items.append(
            ("Books Finished", f"{finished_count} / {total_books}"))

        return stats_items

    def action_dismiss(self) -> None:
        self.dismiss()
