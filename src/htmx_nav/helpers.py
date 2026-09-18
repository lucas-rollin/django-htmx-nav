from collections.abc import Callable
from typing import TypeVar

from django.http import HttpRequest

T = TypeVar("T")

_MISSING = object()


def cache_on_request(request: HttpRequest, key: str, builder: Callable[[], T]) -> T:
    """Cache and return a computed value on the Django request object.

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
