"""
PartialSpec: what template or block to render for a given HTMX request.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias, runtime_checkable

from django.http import HttpRequest

from .targeting import Target, _eval_target


@runtime_checkable
class PartialResolver(Protocol):
    """Derives a partial block or template path from the request and base template."""

    def resolve(self, request: HttpRequest, template_name: str) -> str | None:
        """Resolve a partial block or template path given the request and base template.

        Args:
            request: The incoming HTTP request.
            template_name: The base template path specified by the view.

        Returns:
            A block name (e.g. ``"#content"``), a template path (e.g. ``"partials/_board.html"``),
            or ``None`` to render the full template.
        """
        ...


@dataclass(frozen=True)
class PathReplace:
    """Derive a standalone partial file path by swapping a path segment.

    Legacy/compatibility support for codebases that keep every partial in its
    own file under a directory convention, e.g. ``"pages/"`` -> ``"partials/_"``.

    Args:
        old: The path segment to match (e.g. ``"pages/"``).
        new: The replacement segment (e.g. ``"partials/_"``).
    """

    old: str
    new: str

    def resolve(self, request: HttpRequest, template_name: str) -> str | None:
        """Derive a partial template path by replacing ``old`` with ``new``.

        If ``template_name`` does not contain ``old``, returns ``template_name``
        unmodified so non-matching templates fall back gracefully.
        """
        if template_name and self.old in template_name:
            return template_name.replace(self.old, self.new, 1)
        return template_name


PartialSpec: TypeAlias = (
    str
    | Callable[[HttpRequest], str | None]
    | Mapping[str | PartialResolver, Target]
    | PartialResolver
    | None
)
"""Specifies what template or partial block to render for an HTMX request.

Values resolve to:
    - Block name (``"#name"``): appended to the base template, giving
      ``template.html#name`` (Django 6 ``{% partialdef %}``).
    - Standalone path (``"path/to/template.html"``): rendered in place of the
      base template.
    - Callable ``(request) -> str | None``: returns a block name, path, or
      ``None`` per request.
    - Mapping: keys are block names, paths, or resolvers; values are ``Target``
      conditions. First match wins, so end with ``True`` for a fallback.
    - ``PartialResolver``: derives a block name or path from the request and
      base template name. Advanced extension point; ``PathReplace`` is the
      built-in.
    - ``None``: forces a full-page render.

Examples:
    .. code-block:: python

        "#content"

        lambda request: "#tab_content" if htmx_target_is(request, "tabs") else "#content"

        {
            "#tab_content": targeting("tab-content"),
            "partials/_board.html": targeting("board"),
            "#content": True,
        }

        # Legacy: "pages/board.html" -> "partials/_board.html"
        PathReplace("pages/", "partials/_")
"""


def _resolve_partial_name(
    partial: PartialSpec, request: HttpRequest, template_name: str = ""
) -> str | None:
    """Resolve the active partial or template name for a request."""
    if partial is None:
        return None
    if isinstance(partial, str):
        return partial
    if isinstance(partial, PartialResolver):
        return partial.resolve(request, template_name)
    if isinstance(partial, Mapping):
        for key, target in partial.items():
            if _eval_target(target, request):
                if isinstance(key, PartialResolver):
                    return key.resolve(request, template_name)
                return key
        return None
    if callable(partial):
        return partial(request)
    raise TypeError(f"Invalid PartialSpec value: {partial!r}")


def _resolve_template_name(
    template_name: str,
    partial_name: str | None,
    is_htmx: bool,
) -> str:
    """Resolve the final template path or block string to render."""
    if not is_htmx or not partial_name:
        return template_name
    if partial_name.startswith("#"):
        return f"{template_name}{partial_name}"
    return partial_name
