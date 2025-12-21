#!/usr/bin/env python3
"""Auditui entrypoint."""

import argparse
import sys

from auditui import __version__
from auditui.app import Auditui
from auditui.auth import authenticate
from auditui.configure import configure
from auditui.constants import AUTH_PATH


def main() -> None:
    """Authenticate and launch the app."""
    parser = argparse.ArgumentParser(prog="auditui")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"auditui {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("configure", help="Set up authentication")

    args = parser.parse_args()

    if args.command == "configure":
        try:
            configure()
            print("Configuration completed successfully.")
        except Exception as exc:
            print(f"Configuration error: {exc}")
            sys.exit(1)
        return

    config_dir = AUTH_PATH.parent

    if not config_dir.exists():
        print("No configuration yet, please run 'auditui configure'.")
        sys.exit(1)

    try:
        auth, client = authenticate()
    except Exception as exc:
        print(f"Authentication error: {exc}")
        if not AUTH_PATH.exists():
            print("No configuration yet, please run 'auditui configure'.")
        else:
            print("Please re-authenticate by running 'auditui configure'.")
        sys.exit(1)

    app = Auditui(auth=auth, client=client)
    app.run()


if __name__ == "__main__":
    main()
