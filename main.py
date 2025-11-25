#!/usr/bin/env python3
"""A terminal-based user interface (TUI) client for Audible"""

import sys
from getpass import getpass
from pathlib import Path

import audible
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, DataTable, Static
from textual.worker import get_current_worker
from textual import work


class AudituiApp(App):
    """Main application class for the Audible TUI app."""
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("s", "sort", "Sort by title"),
        ("r", "reverse_sort", "Reverse sort"),
        ("p", "sort_by_progress", "Sort by progress"),
        ("a", "show_all", "Show all books"),
        ("u", "show_unfinished", "Show unfinished"),
        ("q", "quit", "Quit application"),
    ]

    CSS = """
    DataTable {
        height: 1fr;
    }
    Static {
        height: 1;
        text-align: center;
        background: $primary;
    }
    """

    AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"

    def __init__(self):
        super().__init__()
        self.auth = None
        self.client = None
        self.all_items = []
        self.current_items = []
        self.show_all_mode = False
        self.progress_sort_reverse = False
        self.title_column_key = None
        self.progress_column_key = None
        self.progress_column_index = 3

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status")
        table = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table and start fetching library data."""
        table = self.query_one(DataTable)
        table.add_columns("Title", "Author", "Length", "Progress")
        column_keys = list(table.columns.keys())
        self.title_column_key = column_keys[0]
        self.progress_column_key = column_keys[3]
        if self.client:
            self.update_status("Fetching library...")
            self.fetch_library()
        else:
            self.update_status(
                "Not authenticated. Please restart and authenticate.")

    @work(exclusive=True, thread=True)
    def fetch_library(self) -> None:
        """Fetch all library items from Audible API in background thread."""
        worker = get_current_worker()
        if worker.is_cancelled:
            return

        try:
            response_groups = (
                "contributors,media,product_attrs,product_desc,product_details,"
                "rating,is_finished,listening_status,percent_complete"
            )
            all_items = self._fetch_all_pages(response_groups)
            self.all_items = all_items
            self.call_from_thread(self.on_library_loaded, all_items)
        except (OSError, ValueError, KeyError) as e:
            self.call_from_thread(self.on_library_error, str(e))

    def _fetch_all_pages(self, response_groups):
        """Fetch all pages of library items from the API."""
        all_items = []
        page = 1
        page_size = 50

        while True:
            library = self.client.get(
                path="library",
                num_results=page_size,
                page=page,
                response_groups=response_groups
            )

            items = library.get("items", [])

            if not items:
                break

            all_items.extend(items)
            self.call_from_thread(
                self.update_status,
                f"Fetched page {page} ({len(items)} items)..."
            )

            if len(items) < page_size:
                break

            page += 1

        return all_items

    def on_library_loaded(self, items) -> None:
        """Handle successful library load."""
        self.all_items = items
        self.update_status(f"Loaded {len(items)} books")
        self.show_unfinished()

    def on_library_error(self, error: str) -> None:
        """Handle library fetch error."""
        self.update_status(f"Error fetching library: {error}")

    def update_status(self, message: str) -> None:
        """Update the status message in the UI."""
        status = self.query_one("#status", Static)
        status.update(message)

    def format_duration(self, value, unit='minutes', default_none=None):
        """Format duration value into human-readable string."""
        if value is None or value <= 0:
            return default_none

        if unit == 'seconds':
            total_minutes = int(value) // 60
        else:
            total_minutes = int(value)

        if total_minutes < 60:
            return f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"

        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} {mins} minute{'s' if mins != 1 else ''}"

    def _extract_title(self, item):
        """Extract title from library item."""
        product = item.get("product", {})
        return (product.get("title") or
                item.get("title") or
                product.get("asin", "Unknown Title"))

    def _extract_authors(self, item):
        """Extract author names from library item."""
        product = item.get("product", {})
        authors = product.get("authors") or product.get("contributors") or []
        if not authors and "authors" in item:
            authors = item.get("authors", [])
        return ", ".join([a.get("name", "") for a in authors if isinstance(a, dict)])

    def _extract_runtime_minutes(self, item):
        """Extract runtime in minutes from library item."""
        product = item.get("product", {})
        runtime_fields = [
            "runtime_length_min",
            "runtime_length",
            "vLength",
            "length",
            "duration"
        ]

        runtime = None
        for field in runtime_fields:
            runtime = product.get(field)
            if runtime is None:
                runtime = item.get(field)
            if runtime is not None:
                break

        if runtime is None:
            return None

        if isinstance(runtime, dict):
            if "min" in runtime:
                return int(runtime.get("min", 0))
        elif isinstance(runtime, (int, float)):
            return int(runtime)

        return None

    def _extract_progress_info(self, item):
        """Extract progress percentage from library item."""
        percent_complete = item.get("percent_complete")
        listening_status = item.get("listening_status", {})

        if isinstance(listening_status, dict):
            if percent_complete is None:
                percent_complete = listening_status.get("percent_complete")
        else:
            percent_complete = None

        return percent_complete

    def _populate_table(self, items):
        """Populate the DataTable with library items."""
        table = self.query_one(DataTable)
        table.clear()

        if not items:
            self.update_status("No books found.")
            return

        for item in items:
            title = self._extract_title(item)
            author_names = self._extract_authors(item)
            minutes = self._extract_runtime_minutes(item)
            runtime_str = self.format_duration(
                minutes, unit='minutes', default_none="Unknown length")
            percent_complete = self._extract_progress_info(item)

            progress_str = "0%"
            if percent_complete is not None and percent_complete > 0:
                progress_str = f"{percent_complete:.1f}%"

            table.add_row(
                title,
                author_names or "Unknown",
                runtime_str or "Unknown",
                progress_str,
                key=title
            )

        self.current_items = items
        mode = "all" if self.show_all_mode else "unfinished"
        self.update_status(f"Showing {len(items)} books ({mode})")

    def show_all(self) -> None:
        """Display all books in the table."""
        if not self.all_items:
            return
        self.show_all_mode = True
        self._populate_table(self.all_items)

    def show_unfinished(self) -> None:
        """Display only unfinished books in the table."""
        if not self.all_items:
            return
        self.show_all_mode = False

        unfinished_items = []
        for item in self.all_items:
            is_finished_flag = item.get("is_finished")
            percent_complete = item.get("percent_complete")
            listening_status = item.get("listening_status")

            if isinstance(listening_status, dict):
                is_finished_flag = is_finished_flag or listening_status.get(
                    "is_finished", False)
                if percent_complete is None:
                    percent_complete = listening_status.get(
                        "percent_complete", 0)

            is_finished = False
            if is_finished_flag is True:
                is_finished = True
            elif isinstance(percent_complete, (int, float)) and percent_complete >= 100:
                is_finished = True

            if not is_finished:
                unfinished_items.append(item)

        self._populate_table(unfinished_items)

    def action_toggle_dark(self) -> None:
        """Toggle between dark and light theme."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_sort(self) -> None:
        """Sort table by title in ascending order."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.sort(self.title_column_key)

    def action_reverse_sort(self) -> None:
        """Sort table by title in descending order."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.sort(self.title_column_key, reverse=True)

    def action_sort_by_progress(self) -> None:
        """Sort table by progress percentage, toggling direction on each press."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            self.progress_sort_reverse = not self.progress_sort_reverse

            def progress_key(row_values):
                progress_cell = row_values[self.progress_column_index]
                if isinstance(progress_cell, str):
                    try:
                        return float(progress_cell.rstrip("%"))
                    except (ValueError, AttributeError):
                        return 0.0
                return 0.0

            table.sort(key=progress_key, reverse=self.progress_sort_reverse)

    def action_show_all(self) -> None:
        """Action handler to show all books."""
        self.show_all()

    def action_show_unfinished(self) -> None:
        """Action handler to show unfinished books."""
        self.show_unfinished()


def authenticate():
    """Authenticate with Audible and return auth and client objects."""
    auth_path = Path.home() / ".config" / "auditui" / "auth.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    authenticator = None
    if auth_path.exists():
        try:
            authenticator = audible.Authenticator.from_file(str(auth_path))
            audible_client = audible.Client(auth=authenticator)
            return authenticator, audible_client
        except (OSError, ValueError, KeyError) as e:
            print(f"Failed to load existing auth: {e}")
            print("Please re-authenticate.")

    print("Please authenticate with your Audible account.")
    print("You will need to provide:")
    print("  - Your Audible email/username")
    print("  - Your password")
    print("  - Your marketplace locale (e.g., 'US', 'UK', 'DE', 'FR')")

    email = input("\nEmail: ")
    password = getpass("Password: ")
    marketplace = input(
        "Marketplace locale (default: US): ").strip().upper() or "US"

    try:
        authenticator = audible.Authenticator.from_login(
            username=email,
            password=password,
            locale=marketplace
        )

        auth_path.parent.mkdir(parents=True, exist_ok=True)
        authenticator.to_file(str(auth_path))
        print("Authentication successful!")
        audible_client = audible.Client(auth=authenticator)
        return authenticator, audible_client
    except (OSError, ValueError, KeyError) as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    auth, client = authenticate()
    app = AudituiApp()
    app.auth = auth
    app.client = client
    app.run()
