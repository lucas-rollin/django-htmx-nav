from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Union, Protocol

from django.http import HttpRequest
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.cache import patch_vary_headers


@dataclass(frozen=True)
class Swap:
    """
    A fragment rendered alongside the main content in HTMX responses.
    
    Used for out-of-band (OOB) swaps when `target_id` is provided, or as 
    an hx-partial from HTMX v4 when using the `hx-partial` attribute.

    Attributes:
        template_name: Path to the template to render for this fragment.
        context: Optional dictionary of template context.
        target_id: Optional DOM ID to auto-wrap the fragment with an OOB wrapper.
    """
    template_name: str
    context: Optional[dict[str, Any]] = None
    target_id: Optional[str] = None


def _resolve_partial(
        template_name: str, 
        partial_name: Optional[str], 
        is_htmx: bool
    ) -> str:
    """
    Resolve template name with optional Django partial syntax for HTMX requests.

    Args:
        template_name: Base template name.
        partial_name: Name of the partial block to render, or None.
        is_htmx: Whether the current request is an HTMX request.

    Returns:
        Template name with partial suffix if applicable, otherwise base name.
    """
    if not is_htmx or not partial_name:
        return template_name
    return f"{template_name}#{partial_name}"


def _is_htmx_request(request: HttpRequest) -> bool:
    """Return True if the request is from HTMX."""
    htmx_attr = getattr(request, "htmx", None)
    if htmx_attr is not None:
        return bool(htmx_attr)
    return request.headers.get("HX-Request", "") == "true"


def render_htmx(
    request: HttpRequest,
    template_name: str,
    context: Optional[dict] = None,
    content_type: Optional[str] = None,
    status: Optional[int] = None,
    using: Optional[str] = None,
    *,
    partial_name: Optional[str] = "content",
    swaps: Sequence[Swap] = (),
    push_url: Union[bool, str] = False,
) -> TemplateResponse:
    """
    Render a template with HTMX-aware partial and swap support.

    On HTMX requests, it renders only the specified partial (using Django's
    `template.html#partial` syntax) and appends any swap fragments (out-of-band
    or hx-partial fragments). On regular requests, it renders the full template.

    Args:
        request: The Django HTTP request.
        template_name: Base template name to render.
        context: Optional template context dictionary.
        content_type: Optional content type for the response.
        status: Optional HTTP status code.
        using: Optional template engine name to use.

    Keyword Args:
        partial_name: Name of the django partial to render on HTMX requests.
            Defaults to "content". Set to None to disable partial rendering.
        swaps: Sequence of Swap fragments to append on HTMX requests.
        push_url: Controls the HX-Push-Url header:
            - False (default): Don't touch browser history (for non-navigation swaps)
            - True: Push request.get_full_path() to browser history
            - str: Push this explicit URL instead

    Returns:
        TemplateResponse configured for HTMX or regular rendering.

    Raises:
        TemplateDoesNotExist: If the template or partial cannot be found.

    Example:
        ```python
        # Basic usage
        return render_htmx(request, "project/detail.html", {"project": project})
        
        # With swap fragments
        return render_htmx(
            request,
            "project/detail.html",
            {"project": project},
            swaps=[
                Swap("partials/nav.html", {"active": "projects"}, target_id="nav"),
                Swap("partials/notifications.html", target_id="alerts"),
            ],
            push_url=True
        )
        ```
    """
    is_htmx = _is_htmx_request(request)
    context = dict(context or {})
    context.setdefault("active_partial", partial_name)
    resolved_template = _resolve_partial(template_name, partial_name, is_htmx)
    response = TemplateResponse(
        request, resolved_template, context,
        content_type=content_type, status=status, using=using,
    )
    patch_vary_headers(response, ("HX-Request",))
    if is_htmx and push_url:
        response["HX-Push-Url"] = (
            push_url if isinstance(push_url, str) else request.get_full_path()
        )
    if is_htmx and swaps:
        def append_swap(resp):
            for swap in swaps:
                html = render_to_string(
                    swap.template_name, 
                    swap.context or {}, 
                    request=request, 
                    using=using
                )

                if swap.target_id:
                    html = f'<div id="{swap.target_id}" hx-swap-oob="true">{html}</div>'

                resp.content += html.encode(resp.charset)
            return resp
        response.add_post_render_callback(append_swap)
    return response


def _htmx_target_is(target: Optional[str], dom_id: str) -> bool:
    """Match an HX-Target value against a bare DOM id."""
    if not target:
        return False
    return target == dom_id or target == f"#{dom_id}" or target.endswith(f"#{dom_id}")


class ShellRenderer(Protocol):
    def __call__(
        self,
        request: HttpRequest,
        template_name: str,
        context: Optional[dict[str, Any]] = None,
        *,
        extra_swaps: Sequence[Swap] = (),
        partial_name: str = "content",
        **kwargs: Any,
    ) -> TemplateResponse: ...


def make_shell_renderer(
    shell_template: str,
    context_builder: Optional[Callable[[HttpRequest], dict[str, Any]]] = None,
    *,
    page_target_id: Optional[str] = None,
    page_partial_name: str = "content",
)-> ShellRenderer:
    """
    Factory for creating a `render_shell` function with fixed shell swaps.

    Args:
        shell_template: Template path for the shell fragment (e.g., "partials/nav.html").
        context_builder: Optional callable for shell context.
        page_target_id: The DOM ID of the main page content area. Used to
            distinguish between page-level swaps and component-level swaps.

    Returns:
        A `render_shell` function.

    Example:
        ```python
        # Define a shell renderer
        render_page = make_shell_renderer(
            "partials/nav.html",
            context_builder=lambda r: {"user": r.user},
            page_target_id="main-content",
        )

        # Use it inside a Django view to render full or partial responses
        response = render_page(
            request, 
            "project/detail.html", 
            {"project": project}
        )
        ```
    """
    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: Optional[dict[str, Any]] = None,
        *,
        extra_swaps: Sequence[Swap] = (),
        partial_name: str = "content",
        **kwargs,
    ) -> TemplateResponse:
        context = dict(context or {})
        if context_builder is not None:
            context.update(context_builder(request))
        shell_swaps = Swap(shell_template, context)

        if page_target_id is not None:
            htmx = getattr(request, "htmx", None)
            target = getattr(htmx, "target", None) if htmx else None
            if not _is_htmx_request(request) or _htmx_target_is(target, page_target_id):
                partial_name = page_partial_name

        return render_htmx(
            request, template_name, context,
            partial_name=partial_name,
            swaps=(shell_swaps, *extra_swaps),
            **kwargs,
        )
    return render_shell
