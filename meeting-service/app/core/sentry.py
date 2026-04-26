"""Sentry Error Tracking — optional, aktiviert wenn SENTRY_DSN gesetzt."""
from __future__ import annotations

import os


def init_sentry() -> bool:
    """Initialize Sentry if DSN is configured. Returns True if active."""
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("APP_ENV", "development"),
            release=f"nadini-meeting@{os.environ.get('APP_VERSION', '4.0.0')}",
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.1")),
            profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_RATE", "0.1")),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,  # DSGVO: keine personenbezogenen Daten
        )
        return True
    except ImportError:
        return False
