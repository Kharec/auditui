"""Account and subscription data from the API."""

from typing import Any


def get_account_info(client: Any) -> dict:
    if not client:
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
            response = client.get(endpoint, response_groups=response_groups)
            account_info.update(response)
        except Exception:
            pass
    return account_info


def get_subscription_details(account_info: dict) -> dict:
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


def get_country(auth: Any) -> str:
    if not auth:
        return "Unknown"
    try:
        locale_obj = getattr(auth, "locale", None)
        if not locale_obj:
            return "Unknown"
        if hasattr(locale_obj, "country_code"):
            return locale_obj.country_code.upper()
        if hasattr(locale_obj, "domain"):
            return locale_obj.domain.upper()
        if isinstance(locale_obj, str):
            return (
                locale_obj.split("_")[-1].upper()
                if "_" in locale_obj
                else locale_obj.upper()
            )
        return str(locale_obj)
    except Exception:
        return "Unknown"
