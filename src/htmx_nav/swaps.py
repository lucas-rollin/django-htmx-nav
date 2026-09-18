"""
Swap: an out-of-band or <hx-partial> fragment rendered alongside the main
content of an HTMX response.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils.html import conditional_escape
from django.utils.safestring import SafeString

from .debugging import _build_marker_script
from .settings import _debug_swaps_enabled, _default_swap_wrap
from .targeting import Target, _eval_target


@dataclass(frozen=True)
class Swap:
    """Represents an out-of-band (OOB) or `<hx-partial>` fragment for HTMX responses.

    Args:
        template_name: Path to the template or partial (e.g., `"nav.html#sidebar"`).
            Mutually exclusive with `content`. Required unless `swap_style="delete"`
            or `content` is set.
        content: Ready-made fragment body, bypassing template rendering.
            Auto-escaped like a template variable unless wrapped in `mark_safe`.
            Mutually exclusive with `template_name`.
        context: Context mapping for the fragment. Also serves as fallback
            context during full-page renders. Ignored when `content` is set.
        target_id: Target DOM element ID. If `None`, renders without auto-wrapping.
        swap_style: HTMX swap strategy (`"innerHTML"`, `"outerHTML"`, `"delete"`, etc.).
        wrap: Auto-wrap mode (`"oob"` or `"hx-partial"`). Defaults to
            `HTMX_NAV_DEFAULT_SWAP_WRAP` setting. Ignored when `swap_style="delete"`.
        include_if: Predicate determining if the swap applies to the request.

    Raises:
        ValueError: If both or neither of `template_name`/`content` are given
            for a non-delete swap, or if `target_id` is omitted for a delete swap.

    Example:
        .. code-block:: python

            # Standard partial swap
            Swap("partials/sidebar.html", {"active": "home"}, target_id="sidebar")

            # Static string swap
            Swap.text("badge-count", "5")

            # Conditional deletion
            Swap.delete("flash-banner", include_if=targeting("main"))
    """

    template_name: str | None = None
    context: Mapping[str, Any] | None = None
    content: str | None = None
    target_id: str | None = None
    swap_style: str = "innerHTML"
    wrap: Literal["oob", "hx-partial"] | None = None
    include_if: Target = True

    def __post_init__(self) -> None:
        """Applies configured swap-wrap default and validates field combinations."""
        if self.wrap is None:
            object.__setattr__(self, "wrap", _default_swap_wrap())
        if self.swap_style == "delete":
            if self.target_id is None:
                raise ValueError("Swap(swap_style='delete') requires target_id")
        elif self.template_name is not None and self.content is not None:
            raise ValueError("specify only one of template_name or content")
        elif self.template_name is None and self.content is None:
            raise ValueError(
                "template_name or content is required unless swap_style='delete'"
            )

    @classmethod
    def delete(cls, target_id: str, include_if: Target = True) -> "Swap":
        """Builds an OOB delete swap that removes `target_id` from the DOM.

        Equivalent to `<div id="{target_id}" hx-swap-oob="delete"></div>`.

        Args:
            target_id: DOM element ID to remove.
            include_if: Predicate determining if the swap applies to the request.

        Returns:
            A `Swap` configured for deletion.
        """
        return cls(
            target_id=target_id, swap_style="delete", wrap="oob", include_if=include_if
        )

    @classmethod
    def text(
        cls,
        target_id: str,
        content: str,
        swap_style: str = "innerHTML",
        wrap: Literal["oob", "hx-partial"] | None = None,
        include_if: Target = True,
    ) -> "Swap":
        """Builds a swap from a ready-made string, skipping template rendering.

        Args:
            target_id: Target DOM element ID.
            content: The fragment body.
            swap_style: HTMX swap strategy.
            wrap: Auto-wrap mode; defaults to `HTMX_NAV_DEFAULT_SWAP_WRAP`.
            include_if: Predicate determining if the swap applies to the request.

        Returns:
            A `Swap` that renders `content` directly.
        """
        return cls(
            content=content,
            target_id=target_id,
            swap_style=swap_style,
            wrap=wrap,
            include_if=include_if,
        )

    def applies_to(self, request: HttpRequest) -> bool:
        """Evaluates `include_if` against the request to determine inclusion.

        Args:
            request: The incoming HTTP request.

        Returns:
            True if this swap applies to the request.
        """
        return _eval_target(self.include_if, request)

    def render(
        self,
        request: HttpRequest,
        parent_context: Mapping[str, Any] | None = None,
        using: str | None = None,
    ) -> str:
        """Renders the swap to an HTML string.

        Args:
            request: The incoming HTTP request.
            parent_context: Optional parent context to merge with swap context.
            using: Optional template engine name.

        Returns:
            The rendered HTML string, auto-wrapped if `target_id` is set.
        """
        if self.swap_style == "delete":
            # htmx removes the target outright; no body, no wrapper choice,
            # no debug marker (the element won't exist to animate).
            return f'<div id="{self.target_id}" hx-swap-oob="delete"></div>'

        if self.content is not None:
            html: SafeString | str = conditional_escape(self.content)
        else:
            template_name = self.template_name
            assert template_name is not None, (
                "__post_init__ guarantees this outside delete/content"
            )
            final_context = dict(parent_context or {})
            if self.context:
                final_context.update(self.context)
            html = render_to_string(
                template_name,
                final_context,
                request=request,
                using=using,
            )

        if self.target_id and _debug_swaps_enabled():
            html += _build_marker_script(self.target_id)
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


#: Type alias for a single Swap, list/tuple of Swaps, or None.
#: :meta hide-value:
Swaps: TypeAlias = Swap | list[Swap] | tuple[Swap, ...] | None


def _normalize_swaps(swaps: Swaps) -> list[Swap]:
    """Normalizes `Swaps` input into a flat list of `Swap` instances.

    Args:
        swaps: `None`, a single `Swap`, or a list/tuple of `Swap`.

    Returns:
        A list of `Swap` instances. Empty if `swaps` is `None`.
    """
    if swaps is None:
        return []
    if isinstance(swaps, (list, tuple)):
        return list(swaps)
    return [swaps]
