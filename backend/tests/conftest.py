"""Pytest setup: Clerk env vars required before Settings / app import."""

import os

# API startup validates Clerk keys; tests use non-production placeholders.
os.environ.setdefault(
    "CLERK_SECRET_KEY",
    "sk_test_placeholder_for_pytest_only_not_a_real_secret",
)
os.environ.setdefault(
    "CLERK_PUBLISHABLE_KEY",
    "pk_test_placeholder_for_pytest_only_not_a_real_key",
)
# Svix test secret (matches tests/test_clerk_webhook.py signing helpers)
os.environ.setdefault(
    "CLERK_WEBHOOK_SECRET",
    "whsec_dGVzdF9zZWNyZXRmb3JfaW50ZXJuYWxfdGVzdG9ubHk=",
)


def pytest_configure(config):
    from app.config import get_settings

    get_settings.cache_clear()
