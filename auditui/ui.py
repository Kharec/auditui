"""UI components for the Auditui application."""

import json
from datetime import date, datetime
from typing import Any, Callable, Protocol, TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Input, Label, ListItem, ListView, Static

from .constants import AUTH_PATH, CONFIG_PATH

if TYPE_CHECKING:
    from textual.binding import Binding


class _AppContext(Protocol):
    BINDINGS: list[tuple[str, str, str]]
    client: Any
    auth: Any
    library_client: Any
    all_items: list[dict]


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


class AppContextMixin(ModalScreen):
    """Mixin to provide a typed app accessor."""

    def _app(self) -> _AppContext:
        return cast(_AppContext, self.app)


class HelpScreen(AppContextMixin, ModalScreen):
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
    def _parse_binding(binding: "Binding | tuple[str, str, str]") -> tuple[str, str]:
        """Extract key and description from a binding."""
        if isinstance(binding, tuple):
            return binding[0], binding[2]
        return binding.key, binding.description

    def _make_item(self, binding: "Binding | tuple[str, str, str]") -> ListItem:
        """Create a ListItem for a single binding."""
        key, description = self._parse_binding(binding)
        key_display = self._format_key_display(key)
        text = f"[bold {KEY_COLOR}]{key_display:>16}[/]  [{DESC_COLOR}]{description:<25}[/]"
        return ListItem(Label(text))

    def compose(self) -> ComposeResult:
        app = self._app()
        bindings = list(app.BINDINGS)

        with Container(id="help_container"):
            yield Static("Keybindings", id="help_title")
            with Vertical(id="help_content"):
                yield ListView(
                    *[self._make_item(b) for b in bindings],
                    classes="help_list",
                )
            yield Static(
                f"Press [bold {KEY_COLOR}]?[/] or [bold {KEY_COLOR}]Escape[/] to close",
                id="help_footer",
            )

    async def action_dismiss(self, result: Any | None = None) -> None:
        await self.dismiss(result)


class StatsScreen(AppContextMixin, ModalScreen):
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
        app = self._app()
        if not app.client:
            return 0

        current_year = date.today().year

        try:
            stats = app.client.get(
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
                stats = app.client.get(
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
        app = self._app()
        if not app.client:
            return 0

        try:
            stats = app.client.get(
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
        app = self._app()
        if not app.library_client or not app.all_items:
            return 0
        return sum(
            1 for item in app.all_items if app.library_client.is_finished(item)
        )

    def _get_account_info(self) -> dict:
        """Get account information including subscription details."""
        app = self._app()
        if not app.client:
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
                response = app.client.get(
                    endpoint, response_groups=response_groups)
                account_info.update(response)
            except Exception:
                pass

        return account_info

    def _get_email(self) -> str:
        """Get email from auth, config, or API."""
        app = self._app()
        for getter in (
            self._get_email_from_auth,
            self._get_email_from_config,
            self._get_email_from_auth_file,
            self._get_email_from_account_info,
        ):
            email = getter(app)
            if email:
                return email

        auth_data: dict[str, Any] | None = None
        if app.auth:
            try:
                auth_data = getattr(app.auth, "data", None)
            except Exception:
                auth_data = None

        account_info = self._get_account_info() if app.client else None
        for candidate in (auth_data, account_info):
            email = self._find_email_in_data(candidate)
            if email:
                return email

        return "Unknown"

    def _get_email_from_auth(self, app: _AppContext) -> str | None:
        """Extract email from the authenticator if available."""
        if not app.auth:
            return None
        try:
            email = self._first_email(
                getattr(app.auth, "username", None),
                getattr(app.auth, "login", None),
                getattr(app.auth, "email", None),
            )
            if email:
                return email
        except Exception:
            return None

        try:
            customer_info = getattr(app.auth, "customer_info", None)
            if isinstance(customer_info, dict):
                email = self._first_email(
                    customer_info.get("email"),
                    customer_info.get("email_address"),
                    customer_info.get("primary_email"),
                )
                if email:
                    return email
        except Exception:
            return None

        try:
            data = getattr(app.auth, "data", None)
            if isinstance(data, dict):
                return self._first_email(
                    data.get("username"),
                    data.get("email"),
                    data.get("login"),
                    data.get("user_email"),
                )
        except Exception:
            return None
        return None

    def _get_email_from_config(self, app: _AppContext) -> str | None:
        """Extract email from the config file."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return self._first_email(
                        config.get("email"),
                        config.get("username"),
                        config.get("login"),
                    )
        except Exception:
            return None
        return None

    def _get_email_from_auth_file(self, app: _AppContext) -> str | None:
        """Extract email from the auth file."""
        try:
            if AUTH_PATH.exists():
                with open(AUTH_PATH, "r", encoding="utf-8") as f:
                    auth_file_data = json.load(f)
                    return self._first_email(
                        auth_file_data.get("username"),
                        auth_file_data.get("email"),
                        auth_file_data.get("login"),
                        auth_file_data.get("user_email"),
                    )
        except Exception:
            return None
        return None

    def _get_email_from_account_info(self, app: _AppContext) -> str | None:
        """Extract email from the account info API."""
        if not app.client:
            return None
        try:
            account_info = self._get_account_info()
            if account_info:
                email = self._first_email(
                    account_info.get("email"),
                    account_info.get("customer_email"),
                    account_info.get("username"),
                )
                if email:
                    return email
                customer_info = account_info.get("customer_info", {})
                if isinstance(customer_info, dict):
                    return self._first_email(
                        customer_info.get("email"),
                        customer_info.get("email_address"),
                        customer_info.get("primary_email"),
                    )
        except Exception:
            return None
        return None

    def _first_email(self, *values: str | None) -> str | None:
        """Return the first non-empty, non-Unknown email value."""
        for value in values:
            if value and value != "Unknown":
                return value
        return None

    def _find_email_in_data(self, data: Any) -> str | None:
        """Search nested data for an email-like value."""
        if data is None:
            return None

        stack: list[Any] = [data]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)
            elif isinstance(current, str):
                if "@" in current:
                    local, _, domain = current.partition("@")
                    if local and "." in domain:
                        return current
        return None

    def _get_subscription_details(self, account_info: dict) -> dict:
        """Extract subscription details from nested API response."""
        paths = [
            ["customer_details", "subscription", "subscription_details"],
            ["customer", "customer_details", "subscription", "subscription_details"],
            ["subscription_details"],
            ["subscription", "subscription_details"],
        ]
        for path in paths:
            data: Any = account_info
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
        app = self._app()
        if not app.auth:
            return "Unknown"

        try:
            locale_obj = getattr(app.auth, "locale", None)
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
        app = self._app()
        if not app.client:
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
        app = self._app()
        total_books = len(app.all_items) if app.all_items else 0

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

    async def action_dismiss(self, result: Any | None = None) -> None:
        await self.dismiss(result)


class FilterScreen(ModalScreen[str]):
    """Filter screen for searching the library."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        initial_filter: str = "",
        on_change: Callable[[str], None] | None = None,
        debounce_seconds: float = 0.2,
    ) -> None:
        super().__init__()
        self._initial_filter = initial_filter
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._debounce_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Container(id="filter_container"):
            yield Static("Filter Library", id="filter_title")
            yield Input(
                value=self._initial_filter,
                placeholder="Type to filter by title or author...",
                id="filter_input",
            )
            yield Static(
                f"Press [bold {KEY_COLOR}]Enter[/] to apply, "
                f"[bold {KEY_COLOR}]Escape[/] to clear",
                id="filter_footer",
            )

    def on_mount(self) -> None:
        self.query_one("#filter_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self._on_change:
            return
        if self._debounce_timer:
            self._debounce_timer.stop()
        value = event.value
        self._debounce_timer = self.set_timer(
            self._debounce_seconds,
            lambda: self._on_change(value),
        )

    def action_cancel(self) -> None:
        self.dismiss("")

    def on_unmount(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.stop()
