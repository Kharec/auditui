#!/usr/bin/env python3

import sys
from getpass import getpass
from pathlib import Path

try:
    import audible
except ImportError:
    print("Error: audible library not found. Install it with: pip install audible")
    sys.exit(1)


class Auditui:
    AUTH_PATH = Path.home() / ".config" / "auditui" / "auth.json"

    def __init__(self):
        self.auth = None
        self.client = None

    def login_to_audible(self):
        auth_file = self.AUTH_PATH
        auth_file.parent.mkdir(parents=True, exist_ok=True)

        if auth_file.exists():
            try:
                self.auth = audible.Authenticator.from_file(str(auth_file))
                print("Loaded existing authentication.")
                self.client = audible.Client(auth=self.auth)
                return
            except Exception as e:
                print(f"Failed to load existing auth: {e}")
                print("Please re-authenticate.")

        print("Please authenticate with your Audible account.")
        print("You will need to provide:")
        print("  - Your Audible email/username")
        print("  - Your password")
        print("  - Your marketplace locale (e.g., 'US', 'UK', 'DE', 'FR')")

        email = input("Email: ")
        password = getpass("Password: ")
        marketplace = input(
            "Marketplace locale (default: US): ").strip().upper() or "US"

        try:
            self.auth = audible.Authenticator.from_login(
                username=email,
                password=password,
                locale=marketplace
            )

            auth_file.parent.mkdir(parents=True, exist_ok=True)
            self.auth.to_file(str(auth_file))
            print("Authentication successful! Credentials saved.")
            self.client = audible.Client(auth=self.auth)
        except Exception as e:
            print(f"Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def format_duration(value, unit='minutes', default_none=None):
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

    @staticmethod
    def _display_items(items):
        if not items:
            print("No books found.")
            return

        print("-" * 80)

        for idx, item in enumerate(items, 1):
            product = item.get("product", {})

            title = product.get("title")
            if not title:
                title = item.get("title")
            if not title:
                title = product.get("asin", "Unknown Title")

            authors = product.get("authors", [])
            if not authors:
                authors = product.get("contributors", [])
            if not authors and "authors" in item:
                authors = item.get("authors", [])
            author_names = ", ".join([a.get("name", "")
                                     for a in authors if isinstance(a, dict)])

            runtime = None
            runtime_fields = [
                "runtime_length_min",
                "runtime_length",
                "vLength",
                "length",
                "duration"
            ]

            for field in runtime_fields:
                runtime = product.get(field)
                if runtime is None:
                    runtime = item.get(field)
                if runtime is not None:
                    break

            minutes = None
            if isinstance(runtime, dict):
                if "min" in runtime:
                    minutes = int(runtime.get("min", 0))
            elif isinstance(runtime, (int, float)):
                minutes = int(runtime)

            runtime_str = Auditui.format_duration(
                minutes, unit='minutes', default_none="Unknown length")

            percent_complete = item.get("percent_complete")
            listening_status = item.get("listening_status", {})

            if isinstance(listening_status, dict):
                if percent_complete is None:
                    percent_complete = listening_status.get("percent_complete")
                time_remaining_seconds = listening_status.get(
                    "time_remaining_seconds")
            else:
                time_remaining_seconds = None

            print(f"{idx}. {title}")
            if author_names:
                print(f"   Author: {author_names}")
            print(f"   Length: {runtime_str}")

            if percent_complete is not None and percent_complete > 0:
                percent_str = f"{percent_complete:.1f}%"
                print(f"   Progress: {percent_str} read")

                if time_remaining_seconds:
                    time_remaining_str = Auditui.format_duration(
                        time_remaining_seconds, unit='seconds')
                    if time_remaining_str:
                        print(f"   Time remaining: {time_remaining_str}")

            print()

        print("-" * 80)
        print(f"Total: {len(items)} books")

    def _fetch_all_pages(self, response_groups):
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
            print(f"Fetched page {page} ({len(items)} items)...", end="\r")

            if len(items) < page_size:
                break

            page += 1

        return all_items

    def list_library(self):
        try:
            print("\nFetching your library...")

            all_items = self._fetch_all_pages(
                "contributors,media,product_attrs,product_desc,product_details,rating"
            )

            print(f"\nFetched {len(all_items)} books total.\n")

            if not all_items:
                print("Your library is empty.")
                return

            self._display_items(all_items)

        except Exception as e:
            print(f"Error fetching library: {e}")

    def list_unfinished(self):
        try:
            print("\nFetching your library...")

            all_items = self._fetch_all_pages(
                "contributors,media,product_attrs,product_desc,product_details,rating,is_finished,listening_status,percent_complete"
            )

            print(f"\nFetched {len(all_items)} books total.\n")

            unfinished_items = []
            finished_count = 0
            for item in all_items:
                is_finished_flag = item.get("is_finished")
                percent_complete = item.get("percent_complete")
                listening_status = item.get("listening_status")

                if isinstance(listening_status, dict):
                    is_finished_flag = is_finished_flag or listening_status.get(
                        "is_finished", False)
                    percent_complete = percent_complete if percent_complete is not None else listening_status.get(
                        "percent_complete", 0)

                is_finished = False
                if is_finished_flag is True:
                    is_finished = True
                elif isinstance(percent_complete, (int, float)) and percent_complete >= 100:
                    is_finished = True

                if is_finished:
                    finished_count += 1
                else:
                    unfinished_items.append(item)

            print(
                f"Found {len(unfinished_items)} unfinished books (filtered out {finished_count} finished books).\n")

            if not unfinished_items:
                print("No unfinished books found.")
                return

            self._display_items(unfinished_items)

        except Exception as e:
            print(f"Error fetching library: {e}")


def main():
    client = Auditui()
    client.login_to_audible()
    # client.list_library()
    client.list_unfinished()


if __name__ == "__main__":
    main()
