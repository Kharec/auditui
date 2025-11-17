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
    def __init__(self):
        self.auth = None

    def login_to_audible(self):
        auth_file = Path.home() / ".config" / "auditui" / "auth.json"
        auth_file.parent.mkdir(parents=True, exist_ok=True)

        if auth_file.exists():
            try:
                self.auth = audible.Authenticator.from_file(str(auth_file))
                print("Loaded existing authentication.")
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
        except Exception as e:
            print(f"Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    @staticmethod
    def format_runtime(minutes):
        if minutes is None or minutes == 0:
            return "Unknown length"

        minutes = int(minutes)
        if minutes < 60:
            return f"{minutes} minutes"

        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''} {mins} minute{'s' if mins != 1 else ''}"

    def list_library(self):
        client = audible.Client(auth=self.auth)

        try:
            print("\nFetching your library...")

            all_items = []
            page = 1
            page_size = 50

            while True:
                library = client.get(
                    path="library",
                    num_results=page_size,
                    page=page,
                    response_groups="contributors,media,product_attrs,product_desc,product_details,rating"
                )

                items = library.get("items", [])

                if not items:
                    break

                all_items.extend(items)
                print(f"Fetched page {page} ({len(items)} items)...", end="\r")

                if len(items) < page_size:
                    break

                page += 1

            print(f"\nFetched {len(all_items)} books total.\n")

            if not all_items:
                print("Your library is empty.")
                return

            print("-" * 80)

            for idx, item in enumerate(all_items, 1):
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

                runtime_str = self.format_runtime(minutes)

                asin = product.get("asin") or item.get("asin", "")

                print(f"{idx}. {title}")
                if author_names:
                    print(f"   Author: {author_names}")
                print(f"   Length: {runtime_str}")
                if asin:
                    print(f"   ASIN: {asin}")

                print()

            print("-" * 80)
            print(f"Total: {len(all_items)} books")

        except Exception as e:
            print(f"Error fetching library: {e}")
            import traceback
            traceback.print_exc()


def main():
    client = Auditui()
    client.login_to_audible()
    client.list_library()


if __name__ == "__main__":
    main()
