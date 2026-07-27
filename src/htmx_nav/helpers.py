"""
Small, optional helpers for building server-driven HTMX navigation by hand.
Nothing here requires `htmx_nav` to be added to `INSTALLED_APPS` — these
are plain functions you can import and use directly, or copy into your
own project if you'd rather not take the dependency.

See `docs/patterns/` for worked examples of the two most common ways to
turn these into an actual nav (context-processor + template tags, or a
hand-rolled per-project registry).
"""
from typing import Callable, Optional, TypeVar

from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse

T = TypeVar("T")

_MISSING = object()


def reverse_maybe(view_name: Optional[str], kwargs: Optional[dict] = None, *, strict: bool = True) -> Optional[str]:
    """
    `reverse(view_name, kwargs=kwargs)`, with an escape hatch for a very
    common nav situation: a link (e.g. a breadcrumb parent, or a "back to
    list" link) reusing the *current* page's kwargs as a starting point,
    even though the target view doesn't actually accept all of them.

    `strict=True` (default): behaves exactly like `reverse()` — a
    `NoReverseMatch` propagates. Use this when you built `kwargs`
    specifically for `view_name` and a mismatch means your code has a
    real bug.

    `strict=False`: on `NoReverseMatch`, retries once with no kwargs at
    all, and returns that if it succeeds. Use this when `kwargs` are
    *ambient* — e.g. you're passing `request.resolver_match.kwargs`
    through to a handful of different nav links and don't want to hand-
    write "does this particular link need `pk` or not" for every one of
    them.

    Returns `None` if `view_name` is falsy (so callers can write
    `Crumb(label, view_name=None)`-style "current page, not a link"
    entries without a separate branch).

    Example:
        >>> # breadcrumb parent that takes no kwargs, called with the
        >>> # current page's kwargs ({"pk": 7}) — degrades gracefully
        >>> reverse_maybe("app:project_list", {"pk": 7}, strict=False)
        "/projects/"
        >>> # same call, but you meant to pass these kwargs on purpose —
        >>> # a NoReverseMatch here is telling you something is wrong
        >>> reverse_maybe("app:project_list", {"pk": 7}, strict=True)
        Traceback (most recent call last):
            ...
        django.urls.exceptions.NoReverseMatch: ...
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
    """
    Return `getattr(request, key)` if already computed earlier in this
    request; otherwise call `builder()`, store the result on `request`
    under `key`, and return it.

    Useful for anything expensive-ish that the same request might need
    twice in one response cycle — most commonly, computing nav context
    once and reusing it for both the main content render and an OOB
    shell render.

    `key` should be unlikely to collide with anything else on the
    request, e.g. `"_myapp_nav"` rather than `"nav"`.

    Example:
        >>> def build_nav_context(request):
        ...     return cache_on_request(request, "_myapp_nav", lambda: {
        ...         "breadcrumbs": compute_breadcrumbs(request),
        ...     })
    """
    cached = getattr(request, key, _MISSING)
    if cached is not _MISSING:
        return cached # type: ignore[return-value]
    value = builder()
    setattr(request, key, value)
    return value