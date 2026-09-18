"""
Lazily-resolved package settings.

Every getter here re-reads django.conf.settings on each call rather than
caching a module-level constant, so django.test.override_settings works
as expected both in tests and at runtime.
"""

from typing import Literal, cast

from django.conf import settings

_UNSET: object = object()


def _title_context_key() -> str:
    return str(getattr(settings, "HTMX_NAV_TITLE_CONTEXT_KEY", "title"))


def _default_swap_wrap() -> Literal["oob", "hx-partial"]:
    return cast(
        Literal["oob", "hx-partial"],
        getattr(settings, "HTMX_NAV_DEFAULT_SWAP_WRAP", "oob"),
    )


def _default_partial_spec() -> str:
    return str(getattr(settings, "HTMX_NAV_DEFAULT_PARTIAL", "#content"))


def _debug_swaps_enabled() -> bool:
    """Resolve whether debug swaps are enabled lazily for test override support."""
    return bool(getattr(settings, "HTMX_NAV_DEBUG_SWAPS", False))
