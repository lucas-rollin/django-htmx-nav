"""
Swap: an out-of-band or <hx-partial> fragment rendered alongside the main
content of an HTMX response.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from django.http import HttpRequest
from django.template.loader import render_to_string

from .settings import _debug_swaps_enabled, _default_swap_wrap
from .targeting import Target, _eval_target


def _debug_marker_script(target_id: str) -> str:
    """
    Inline script marking a swapped element for htmx-nav's visual debug tool.

    Survives wrapper-stripping on innerHTML-style OOB/hx-partial swaps
    because it's emitted as a sibling of the fragment's own content, inside
    the wrapper — both get inserted as children of the real target
    regardless of swap style, so the script always ends up in the DOM.
    Class is re-applied with a forced reflow so repeated swaps of the same
    (non-replaced) element retrigger the CSS animation each time.
    """
    return (
        "<script>(function(){"
        f"var el=document.getElementById({json.dumps(target_id)});"
        "if(!el)return;"
        "el.classList.remove('hn-swap');void el.offsetWidth;"
        "el.classList.add('hn-swap');"
        "})();</script>"
    )


@dataclass(frozen=True)
class Swap:
    """Represents an out-of-band (OOB) or `<hx-partial>` fragment for HTMX responses.

    Attributes:
        template_name: Path to the template or partial (e.g., `"nav.html#sidebar"`).
        context: Context mapping for the fragment. Also serves as fallback
            context during full-page renders.
        target_id: Target DOM element ID. If `None`, renders without auto-wrapping.
        swap_style: HTMX swap strategy (`"innerHTML"`, `"outerHTML"`, etc.).
        wrap: Auto-wrap mode (`"oob"` or `"hx-partial"`). Defaults to
            `HTMX_NAV_DEFAULT_SWAP_WRAP` setting.
        include_if: Predicate determining if the swap applies to the request.
    """

    template_name: str
    context: Mapping[str, Any] | None = None
    target_id: str | None = None
    swap_style: str = "innerHTML"
    wrap: Literal["oob", "hx-partial"] | None = None
    include_if: Target = True

    def __post_init__(self) -> None:
        if self.wrap is None:
            object.__setattr__(self, "wrap", _default_swap_wrap())

    def applies_to(self, request: HttpRequest) -> bool:
        """Determines whether this swap should be included for the request."""
        return _eval_target(self.include_if, request)

    def render(
        self,
        request: HttpRequest,
        parent_context: Mapping[str, Any] | None = None,
        using: str | None = None,
    ) -> str:
        """Renders the swap fragment to an HTML string, wrapped for OOB/
        hx-partial delivery when `target_id` is set."""
        final_context = dict(parent_context or {})
        if self.context:
            final_context.update(self.context)

        html = render_to_string(
            self.template_name,
            final_context,
            request=request,
            using=using,
        )

        if self.target_id and _debug_swaps_enabled():
            html += _debug_marker_script(self.target_id)

        if not self.target_id:
            return html

        if self.wrap == "hx-partial":
            return (
                f'<hx-partial hx-target="#{self.target_id}" '
                f'hx-swap="{self.swap_style}">{html}</hx-partial>'
            )

        return (
            f'<div id="{self.target_id}" hx-swap-oob="{self.swap_style}">{html}</div>'
        )


Swaps: TypeAlias = Swap | list[Swap] | tuple[Swap, ...] | None


def _normalize_swaps(swaps: Swaps) -> list[Swap]:
    """Normalizes `Swaps` input into a flat list of `Swap` instances."""
    if swaps is None:
        return []
    if isinstance(swaps, (list, tuple)):
        return list(swaps)
    return [swaps]
