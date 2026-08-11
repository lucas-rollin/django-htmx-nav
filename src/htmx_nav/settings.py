"""
Lazily-resolved package settings.

Every getter here re-reads django.conf.settings on each call rather than
caching a module-level constant, so django.test.override_settings works
as expected both in tests and at runtime.
"""

from typing import Literal, cast

from django.conf import settings


def _title_context_key() -> str:
    return str(getattr(settings, "HTMX_NAV_TITLE_CONTEXT_KEY", "title"))


def _default_swap_wrap() -> Literal["oob", "hx-partial"]:
    return cast(
        Literal["oob", "hx-partial"],
        getattr(settings, "HTMX_NAV_DEFAULT_SWAP_WRAP", "oob"),
    )


def _debug_swaps_enabled() -> bool:
    """Resolved lazily (not cached), same pattern as the other settings
    getters, so override_settings works in tests."""
    return bool(getattr(settings, "HTMX_NAV_DEBUG_SWAPS", False))
