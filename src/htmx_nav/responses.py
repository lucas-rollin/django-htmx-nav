import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias, cast

from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.cache import patch_vary_headers
from django.utils.html import escape

# ---------------------------------------------------------------------------
# Settings — resolved lazily (never cached at import time) so that
# django.test.override_settings works as expected in tests and at runtime.
# ---------------------------------------------------------------------------


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

# ---------------------------------------------------------------------------
# Core public types
# ---------------------------------------------------------------------------


Target: TypeAlias = str | Callable[[HttpRequest], bool] | bool
"""Condition deciding whether a partial or swap applies to an HTMX request.

Examples:
    ```python
    "main-content"  # Matches HX-Target header
    targeting("main-content", "modal")
    not_targeting("sidebar")
    True
    False
    ```
"""


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
    # Render a specific partial block in the same template used in `render_htmx`
    "#content"

    # Render a standalone partial template
    "partials/_tab_content.html"

    # Render a django partial in another template
    "partials/navigation_components.html#sidebar"

    # Dynamic target resolution via callable
    lambda request: "#tab_content" if htmx_target_is(request, "tabs") else "#content"

    # First matching Target key wins
    {
        "partials/_tab_content.html": targeting("tabs"),
        "#main_content": targeting("main"),
        "#content": True,
    }
    ```
"""


# ---------------------------------------------------------------------------
# Swap
# ---------------------------------------------------------------------------


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
        """Determines whether this swap should be included for the request.

        Args:
            request: The incoming HTTP request.

        Returns:
            True if the swap condition evaluates to True, False otherwise.
        """
        return _eval_target(self.include_if, request)

    def render(
        self,
        request: HttpRequest,
        parent_context: Mapping[str, Any] | None = None,
        using: str | None = None,
    ) -> str:
        """Renders the swap fragment to an HTML string.

        Args:
            request: The incoming HTTP request.
            parent_context: Ambient context merged beneath `self.context`.
            using: Optional template engine name.

        Returns:
            The rendered HTML string, wrapped in an OOB container if `target_id` is set.
        """
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


def _debug_marker_script(target_id: str) -> str:
    """
    Inline script marking a swapped element for htmx-nav's visual debug tool. 
    
    Survives wrapper-stripping on innerHTML-style OOB/hx-partial
    swaps because it's emitted as a sibling of the fragment's own content,
    inside the wrapper, both get inserted as children of the real target
    regardless of swap style, so the script always ends up in the DOM.
    Class is re-applied with a forced reflow so repeated swaps of the
    same (non-replaced) element retrigger the CSS animation each time.
    """
    return (
        "<script>(function(){"
        f"var el=document.getElementById({json.dumps(target_id)});"
        "if(!el)return;"
        "el.classList.remove('hn-swap');void el.offsetWidth;"
        "el.classList.add('hn-swap');"
        "})();</script>"
    )

# ---------------------------------------------------------------------------
# HTMX target helpers
# ---------------------------------------------------------------------------


def _is_htmx_request(request: HttpRequest) -> bool:
    """Determines whether the request is an HTMX request."""
    htmx_attr = getattr(request, "htmx", None)
    if htmx_attr is not None:
        return bool(htmx_attr)
    return request.headers.get("HX-Request", "") == "true"


def _htmx_target_header(request: HttpRequest) -> str | None:
    """Resolve the effective HX-Target value for this request.

    Prefers request.htmx.target (django-htmx) when django-htmx's middleware has
    populated it; otherwise falls back to reading the raw HX-Target header directly.
    """
    htmx = getattr(request, "htmx", None)
    if htmx is not None:
        return getattr(htmx, "target", None)
    return request.headers.get("HX-Target")


def _dom_id(value: str) -> str:
    """Normalizes selector strings like 'div#foo' or '#foo' to 'foo'."""
    return value.rsplit("#", 1)[-1]


def _htmx_target_is(target: str | None, dom_id: str) -> bool:
    """Checks if an HX-Target header matches a DOM ID across HTMX versions."""
    if not target:
        return False
    return _dom_id(target) == _dom_id(dom_id)


def htmx_target_is(request: HttpRequest, *dom_ids: str) -> bool:
    """Checks if the request's `HX-Target` header matches any given DOM ID.

    Args:
        request: The incoming HTTP request.
        *dom_ids: DOM element IDs to match against (e.g., `"content"`, `"#content"`).

    Returns:
        True if the request target matches any provided ID.

    Example:
        ```python
        if htmx_target_is(request, "tab-content", "modal-body"):
            ...
        ```
    """
    target = _htmx_target_header(request)
    return any(_htmx_target_is(target, dom_id) for dom_id in dom_ids)


def targeting(*dom_ids: str) -> Callable[[HttpRequest], bool]:
    """Creates a predicate checking if a request targets any specified DOM ID.

    Args:
        *dom_ids: Target DOM IDs to check.

    Returns:
        A callable accepting an `HttpRequest` and returning a boolean.

    Example:
        ```python
        Swap(
            "partials/tabs.html",
            target_id="tabs",
            include_if=targeting("tab-content", "tabs"),
        )
        ```
    """

    def predicate(request: HttpRequest) -> bool:
        return htmx_target_is(request, *dom_ids)

    return predicate


def not_targeting(*dom_ids: str) -> Callable[[HttpRequest], bool]:
    """Creates a predicate checking that a request does NOT target specified DOM IDs.

    Args:
        *dom_ids: Target DOM IDs to exclude.

    Returns:
        A callable accepting an `HttpRequest` and returning a boolean.

    Example:
        ```python
        Swap(
            "partials/sidebar.html",
            target_id="sidebar",
            include_if=not_targeting("main-content"),
        )
        ```
    """

    def predicate(request: HttpRequest) -> bool:
        return not htmx_target_is(request, *dom_ids)

    return predicate


def _eval_target(spec: Target, request: HttpRequest) -> bool:
    """Evaluates a `Target` specification against an HTTP request."""
    if spec is True:
        return True
    if spec is False:
        return False
    if isinstance(spec, str):
        return htmx_target_is(request, spec)
    if callable(spec):
        return bool(spec(request))
    raise TypeError(f"Invalid Target value: {spec!r}")


# ---------------------------------------------------------------------------
# Partial resolution
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------


def render_htmx(
    request: HttpRequest,
    template_name: str,
    context: Mapping[str, Any] | None = None,
    content_type: str | None = None,
    status: int | None = None,
    using: str | None = None,
    *,
    partial: PartialSpec = "#content",
    swaps: Swaps = None,
    title: str | None = None,
) -> TemplateResponse:
    """Renders a Django template with HTMX partial resolution and OOB swaps.

    Args:
        request: The Django HTTP request.
        template_name: Path to the base template.
        context: Primary template context.
        content_type: MIME type for the response.
        status: HTTP status code.
        using: Template engine name to use.
        partial: Partial spec deciding what region to render. Defaults to `"#content"`.
        swaps: One or more `Swap` objects to append to HTMX responses.
        title: Page title. Sets context title and appends `<title>` tag for HTMX responses.

    Returns:
        Configured `TemplateResponse` object.

    Example:
        ```python
        return render_htmx(
            request,
            "project/detail.html",
            {"project": project},
            partial={
                "#tab_content": targeting("tab-content"),
                "#main_content": targeting("main-content"),
                "#content": True,
            },
            swaps=[
                Swap("partials/sidebar.html", target_id="sidebar"),
            ],
            title=project.name,
        )
        ```
    """
    is_htmx = _is_htmx_request(request)
    swap_list = _normalize_swaps(swaps)

    base_context: dict[str, Any] = {}
    for swap in swap_list:
        if swap.context:
            base_context.update(swap.context)

    page_context = {**base_context, **(context or {})}

    active_partial = _resolve_partial_name(partial, request)
    page_context.setdefault("active_partial", active_partial)

    title_key = _title_context_key()
    page_context.setdefault(title_key, None)
    if title is not None:
        page_context[title_key] = title
    effective_title = page_context.get(title_key)

    resolved_template = _resolve_template_name(template_name, active_partial, is_htmx)

    response = TemplateResponse(
        request,
        resolved_template,
        page_context,
        content_type=content_type,
        status=status,
        using=using,
    )
    patch_vary_headers(response, ("HX-Request",))

    if is_htmx and (swap_list or effective_title):

        def append_swaps(response: TemplateResponse) -> TemplateResponse:
            for swap in swap_list:
                if not swap.applies_to(request):
                    continue

                html = swap.render(
                    request,
                    parent_context=page_context,
                    using=using,
                )
                response.content += html.encode(response.charset)

            if effective_title:
                response.content += f"<title>{escape(effective_title)}</title>".encode(
                    response.charset
                )

            return response

        response.add_post_render_callback(append_swaps)

    return response


# ---------------------------------------------------------------------------
# Shell renderer
# ---------------------------------------------------------------------------


class ShellRenderer(Protocol):
    """Callable signature for renderers produced by `make_shell_renderer`."""

    def __call__(
        self,
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec = "#content",
        **kwargs: Any,
    ) -> TemplateResponse: ...


def make_shell_renderer(
    shell_template: str,
    context_builder: Callable[[HttpRequest], Mapping[str, Any]] | None = None,
    *,
    target_id: str | None = None,
    include_if: Target = True,
    namespace: str | None = None,
    partial: PartialSpec = "#content",
) -> ShellRenderer:
    """Creates a renderer that automatically injects a shell navigation swap.

    Args:
        shell_template: Template path for the shell/navigation component.
        context_builder: Callable supplying context for the shell template.
        target_id: Target DOM ID for the shell swap.
        include_if: Condition governing when the shell swap renders.
        namespace: Context key under which shell context is scoped.
        partial: Default `PartialSpec` for responses created by this renderer.

    Returns:
        A `ShellRenderer` instance preconfigured with the shell swap logic.

    Example:
        ```python
        render_dashboard = make_shell_renderer(
            "partials/navigation.html",
            context_builder=lambda req: {"unread": req.user.unread_count},
            target_id="nav-bar",
        )

        return render_dashboard(request, "pages/projects.html", {"projects": projects})
        ```
    """
    default_partial: PartialSpec = (
        dict(partial) if isinstance(partial, Mapping) else partial
    )

    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: Mapping[str, Any] | None = None,
        *,
        extra_swaps: Swaps = None,
        partial: PartialSpec = default_partial,
        **kwargs: Any,
    ) -> TemplateResponse:
        page_context = dict(context or {})
        shell_context = dict(
            context_builder(request) if context_builder is not None else {}
        )

        if namespace is not None:
            shell_swap_context: dict[str, Any] = {namespace: shell_context}
        else:
            shell_swap_context = {**shell_context, **page_context}

        shell_swap = Swap(
            shell_template,
            context=shell_swap_context,
            target_id=target_id,
            include_if=include_if,
        )

        return render_htmx(
            request,
            template_name,
            page_context,
            partial=partial,
            swaps=[shell_swap, *_normalize_swaps(extra_swaps)],
            **kwargs,
        )

    return render_shell
