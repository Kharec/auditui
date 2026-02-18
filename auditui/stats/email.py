"""Email resolution from auth, config, auth file, and account API."""

import json
from pathlib import Path
from typing import Any, Callable

from ..constants import AUTH_PATH, CONFIG_PATH


def find_email_in_data(data: Any) -> str | None:
    if data is None:
        return None
    stack = [data]
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


def first_email(*values: str | None) -> str | None:
    for value in values:
        if value and value != "Unknown":
            return value
    return None


def get_email_from_auth(auth: Any) -> str | None:
    if not auth:
        return None
    try:
        email = first_email(
            getattr(auth, "username", None),
            getattr(auth, "login", None),
            getattr(auth, "email", None),
        )
        if email:
            return email
    except Exception:
        return None
    try:
        customer_info = getattr(auth, "customer_info", None)
        if isinstance(customer_info, dict):
            email = first_email(
                customer_info.get("email"),
                customer_info.get("email_address"),
                customer_info.get("primary_email"),
            )
            if email:
                return email
    except Exception:
        return None
    try:
        data = getattr(auth, "data", None)
        if isinstance(data, dict):
            return first_email(
                data.get("username"),
                data.get("email"),
                data.get("login"),
                data.get("user_email"),
            )
    except Exception:
        return None
    return None


def get_email_from_config(config_path: Path | None = None) -> str | None:
    path = config_path or CONFIG_PATH
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return first_email(
                    config.get("email"),
                    config.get("username"),
                    config.get("login"),
                )
    except Exception:
        return None
    return None


def get_email_from_auth_file(auth_path: Path | None = None) -> str | None:
    path = auth_path or AUTH_PATH
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                auth_file_data = json.load(f)
                return first_email(
                    auth_file_data.get("username"),
                    auth_file_data.get("email"),
                    auth_file_data.get("login"),
                    auth_file_data.get("user_email"),
                )
    except Exception:
        return None
    return None


def get_email_from_account_info(account_info: dict) -> str | None:
    email = first_email(
        account_info.get("email"),
        account_info.get("customer_email"),
        account_info.get("username"),
    )
    if email:
        return email
    customer_info = account_info.get("customer_info", {})
    if isinstance(customer_info, dict):
        return first_email(
            customer_info.get("email"),
            customer_info.get("email_address"),
            customer_info.get("primary_email"),
        )
    return None


def resolve_email(
    auth: Any,
    client: Any,
    config_path: Path | None = None,
    auth_path: Path | None = None,
    get_account_info: Callable[[], dict] | None = None,
) -> str:
    config_path = config_path or CONFIG_PATH
    auth_path = auth_path or AUTH_PATH
    for getter in (
        lambda: get_email_from_auth(auth),
        lambda: get_email_from_config(config_path),
        lambda: get_email_from_auth_file(auth_path),
        lambda: get_email_from_account_info(
            get_account_info()) if get_account_info else None,
    ):
        email = getter()
        if email:
            return email
    auth_data = None
    if auth:
        try:
            auth_data = getattr(auth, "data", None)
        except Exception:
            pass
    account_info = get_account_info() if get_account_info else {}
    for candidate in (auth_data, account_info):
        email = find_email_in_data(candidate)
        if email:
            return email
    return "Unknown"
