"""
PartialSpec: what template or block to render for a given HTMX request.
"""

from collections.abc import Callable, Mapping
from typing import TypeAlias

from django.http import HttpRequest

from .targeting import Target, _eval_target

PartialSpec: TypeAlias = (
    str | Callable[[HttpRequest], str | None] | Mapping[str, Target] | None
)
"""Specifies what template or partial block to render for an HTMX request.

Values resolve to:
    - Block name (`"#name"`): Appended to base template as `template.html#name`.
    - Standalone path (`"path/to/template.html"`): Renders in place of base template.
    - `None`: Forces a full-page render.

Examples:
```python
    "#content"

    "partials/_tab_content.html"

    "partials/navigation_components.html#sidebar"

    lambda request: "#tab_content" if htmx_target_is(request, "tabs") else "#content"

    {
        "partials/_tab_content.html": targeting("tabs"),
        "#main_content": targeting("main"),
        "#content": True,
    }
```
"""


def _resolve_partial_name(partial: PartialSpec, request: HttpRequest) -> str | None:
    """Resolves the active partial or template name for a request."""
    if partial is None:
        return None
    if isinstance(partial, str):
        return partial
    if isinstance(partial, Mapping):
        for name, target in partial.items():
            if _eval_target(target, request):
                return name
        return None
    if callable(partial):
        return partial(request)
    raise TypeError(f"Invalid PartialSpec value: {partial!r}")


def _resolve_template_name(
    template_name: str,
    partial_name: str | None,
    is_htmx: bool,
) -> str:
    """Resolves the final template path or block string to render."""
    if not is_htmx or not partial_name:
        return template_name
    if partial_name.startswith("#"):
        return f"{template_name}{partial_name}"
    return partial_name
