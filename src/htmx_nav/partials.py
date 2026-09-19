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

    def resolve(self, request: HttpRequest, template_name: str) -> str | None: ...


@dataclass(frozen=True)
class ReplacePrefix:
    """Swap a path prefix or directory segment, e.g. ``"pages/"`` -> ``"partials/_"``."""

    old: str
    new: str

    def resolve(self, request: HttpRequest, template_name: str) -> str | None:
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
    - Block name (``"#name"``): Appended to base template as ``template.html#name``.
    - Standalone path (``"path/to/template.html"``): Renders in place of base template.
    - ``None``: Forces a full-page render.

Examples:
    .. code-block:: python

        "#content" # Django 6 native inline partial

        PartialResolver("pages/", "partials/_") # standalone partial

        "partials/_tab_content.html"

        "partials/navigation_components.html#sidebar"

        lambda request: "#tab_content" if htmx_target_is(request, "tabs") else "#content"

        {
            "partials/_tab_content.html": targeting("tabs"),
            "#main_content": targeting("main"),
            "#content": True,
        }
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
