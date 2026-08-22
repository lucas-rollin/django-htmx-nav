from collections.abc import Callable
from typing import Any, TypeVar

from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse

T = TypeVar("T")

_MISSING = object()


def reverse_maybe(
    view_name: str | None,
    kwargs: dict[str, Any] | None = None,
    *,
    strict: bool = True,
) -> str | None:
    """Reverses a URL with an optional fallback for unmatched keyword arguments.

    Args:
        view_name: The name of the view to reverse.
        kwargs: Keyword arguments for the view.
        strict: If True, raises NoReverseMatch on failure. If False, retries
            once without kwargs before raising.

    Returns:
        The reversed URL string, or None if view_name is falsy.

    Raises:
        NoReverseMatch: If the URL cannot be reversed and strict is True.
    """
    if not view_name:
        return None
    try:
        return reverse(view_name, kwargs=kwargs or {})
    except NoReverseMatch:
        if strict or not kwargs:
            raise
        return reverse(view_name)


def cache_on_request(request: HttpRequest, key: str, builder: Callable[[], T]) -> T:
    """Caches and returns a computed value on the Django request object.

    Args:
        request: The Django HTTP request.
        key: The attribute name to store the cached value under.
        builder: A callable that generates the value if not already cached.

    Returns:
        The cached or newly computed value.
    """
    cached = getattr(request, key, _MISSING)
    if cached is not _MISSING:
        return cached  # type: ignore[return-value]
    value = builder()
    setattr(request, key, value)
    return value
