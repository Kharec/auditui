#!/usr/bin/env python3
"""Auditui entrypoint."""

from auditui.app import Auditui
from auditui.auth import authenticate


def main() -> None:
    """Authenticate and launch the app."""
    auth, client = authenticate()
    app = Auditui(auth=auth, client=client)
    app.run()


if __name__ == "__main__":
    main()
