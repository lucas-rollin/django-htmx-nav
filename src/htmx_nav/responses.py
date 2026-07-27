from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Union

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.cache import patch_vary_headers


@dataclass(frozen=True)
class Oob:
    """
    Defines an out-of-band fragment rendered alongside the main content.

    Out-of-band (OOB) swaps allow HTMX to update multiple elements on the page
    in a single response. This class represents one such fragment that will be
    rendered and appended to the response.

    Attributes:
        template_name: Path to the template to render for this fragment.
        context: Optional dictionary of template context. If None, the fragment
            will use context processors and template tags for data.
        target_id: Optional DOM ID to auto-wrap the fragment with an OOB wrapper.
            If provided, renders as: <div id="{target_id}" hx-swap-oob="true">...
            If None, the template itself must provide the OOB wrapper markup.

    Example:
        >>> # Simple OOB with auto-wrap
        >>> Oob("partials/notification.html", {"message": "Saved"}, target_id="alerts")
        >>> 
        >>> # Complex OOB with template-provided wrapper
        >>> Oob("partials/dashboard.html", {"data": dashboard_data})
    """
    template_name: str
    context: Optional[dict[str, Any]] = None
    target_id: Optional[str] = None


def _with_partial(template_name: str, partial_name: Optional[str], is_htmx: bool) -> str:
    """
    Resolve template name with optional partial syntax for HTMX requests.

    Django's template partial syntax (`template.html#partial`) allows rendering
    only a specific {% partial %} block from a template. This is used to return
    just the content area on HTMX requests while still rendering the full
    template on full page loads.

    Args:
        template_name: Base template name.
        partial_name: Name of the partial block to render, or None.
        is_htmx: Whether the current request is an HTMX request.

    Returns:
        Template name with partial suffix if applicable, otherwise base name.

    Example:
        >>> _with_partial("page.html", "content", True)
        "page.html#content"
        >>> _with_partial("page.html", None, True)
        "page.html"
    """
    if not is_htmx or not partial_name:
        return template_name
    return f"{template_name}#{partial_name}"


def _is_htmx_request(request: HttpRequest) -> bool:
    """
    Determine if the request is an HTMX request.

    Works with or without django-htmx installed. If django-htmx's middleware
    is enabled, prefers `request.htmx` for compatibility with other code that
    may rely on its extra attributes (`.boosted`, `.trigger`, `.target`, etc.).

    Falls back to reading the `HX-Request` header directly. HTMX always sends
    `HX-Request: true` on requests it issues, so this fallback is fully
    sufficient for `render_htmx`'s own needs.

    Note:
        django-htmx is not required for out-of-band rendering to work. It's
        only worth adding to a project if you want its richer `request.htmx`
        API elsewhere.

    Args:
        request: The Django HTTP request.

    Returns:
        True if the request is an HTMX request, False otherwise.

    Example:
        >>> _is_htmx_request(request)  # True if HX-Request header present
        True
    """
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
    oobs: Sequence[Oob] = (),
    push_url: Union[bool, str] = True,
) -> TemplateResponse:
    """
    Render a template with HTMX-aware partial and out-of-band support.

    This is the core function for building HTMX-responsive views. On HTMX
    requests, it renders only the specified partial (using Django's
    `template.html#partial` syntax) and appends any out-of-band fragments.
    On regular requests, it renders the full template.

    The URL is treated as the single source of truth for page state:
      - Pushes the canonical URL to browser history on HTMX requests
      - Sets `Vary: HX-Request` for proper caching behavior
      - Makes deep-swapped state bookmarkable and reload-safe

    Args:
        request: The Django HTTP request.
        template_name: Base template name to render.
        context: Optional template context dictionary.
        content_type: Optional content type for the response.
        status: Optional HTTP status code.
        using: Optional template engine name to use.

    Keyword Args:
        partial_name: Name of the partial block to render on HTMX requests.
            Defaults to "content". Set to None to disable partial rendering.
        oobs: Sequence of Oob fragments to append on HTMX requests.
        push_url: Controls the HX-Push-Url header:
            - True (default): Push request.get_full_path() to browser history
            - str: Push this explicit URL instead
            - False: Don't touch browser history (for non-navigation swaps)

    Returns:
        TemplateResponse configured for HTMX or regular rendering.

    Raises:
        TemplateDoesNotExist: If the template or partial cannot be found.

    Example:
        >>> # Basic usage
        >>> return render_htmx(request, "project/detail.html", {"project": project})
        >>> 
        >>> # With OOB fragments
        >>> return render_htmx(
        ...     request,
        ...     "project/detail.html",
        ...     {"project": project},
        ...     oobs=[
        ...         Oob("partials/nav.html", {"active": "projects"}, target_id="nav"),
        ...         Oob("partials/notifications.html", target_id="alerts"),
        ...     ]
        ... )
        >>> 
        >>> # Non-navigation swap (don't push URL)
        >>> return render_htmx(
        ...     request,
        ...     "partials/task_list.html",
        ...     {"tasks": tasks},
        ...     push_url=False,
        ... )
    """
    is_htmx = _is_htmx_request(request)
    context = dict(context or {})
    context.setdefault("active_partial", partial_name)
    resolved_template = _with_partial(template_name, partial_name, is_htmx)
    response = TemplateResponse(
        request, resolved_template, context,
        content_type=content_type, status=status, using=using,
    )
    patch_vary_headers(response, ("HX-Request",))
    if is_htmx and push_url:
        response["HX-Push-Url"] = (
            push_url if isinstance(push_url, str) else request.get_full_path()
        )
    if is_htmx and oobs:
        def append_oob(resp):
            for oob in oobs:
                html = render_to_string(
                    oob.template_name, 
                    oob.context or {}, 
                    request=request, 
                    using=using
                )

                if oob.target_id:
                    html = f'<div id="{oob.target_id}" hx-swap-oob="true">{html}</div>'

                resp.content += html.encode(resp.charset)
            return resp
        response.add_post_render_callback(append_oob)
    return response


def htmx_redirect(request: HttpRequest, url: str) -> HttpResponse:
    """
    Redirect to a URL, handling HTMX requests correctly.

    A plain `HttpResponseRedirect` doesn't work as expected inside an HTMX
    swap: htmx follows the redirect via XHR and swaps the redirected page's
    HTML into the original target, rather than navigating the browser.

    On HTMX requests, this returns an empty 204 response with `HX-Redirect`
    header, which tells htmx to perform a full client-side navigation. On
    regular requests, it returns a standard redirect.

    Args:
        request: The Django HTTP request.
        url: The URL to redirect to.

    Returns:
        HttpResponse: A 204 response with HX-Redirect header for HTMX requests,
            or a standard HttpResponseRedirect for regular requests.

    Example:
        >>> def my_view(request):
        ...     if form.is_valid():
        ...         return htmx_redirect(request, reverse("project-detail", args=[obj.pk]))
        ...     return render_htmx(request, "form.html", {"form": form})
        >>> 
        >>> # On HTMX request: returns 204 with HX-Redirect: /projects/1/
        >>> # On regular request: returns 302 redirect
    """
    if _is_htmx_request(request):
        return HttpResponse(status=204, headers={"HX-Redirect": url})
    return HttpResponseRedirect(url)


def make_shell_renderer(
    shell_template: str,
    context_builder: Optional[Callable[[HttpRequest], dict]] = None,
):
    """
    Factory for creating a `render_shell` function with a fixed OOB shell.

    The shell renderer wraps `render_htmx` to automatically include a shell
    (e.g., navigation, header, footer) as an out-of-band fragment on every
    HTMX response. This allows the shell to be updated independently from the
    main content, enabling persistent UI elements like navigation menus.

    Args:
        shell_template: Template path for the shell fragment (e.g., "partials/nav.html").
        context_builder: Optional callable that takes request and returns context
            dict for the shell. This is useful for injecting data like current
            user info, workspace data, or navigation state. If None, the shell
            receives only the page's own context.

    Returns:
        A `render_shell` function with the following signature:
            render_shell(
                request: HttpRequest,
                template_name: str,
                context: Optional[dict] = None,
                *,
                extra_oob: Sequence[Oob] = (),
                **kwargs
            ) -> TemplateResponse

    Example:
        >>> def build_nav_context(request):
        ...     return {
        ...         "user": request.user,
        ...         "workspace": get_active_workspace(request),
        ...         "nav_items": get_nav_items(request),
        ...     }
        >>> 
        >>> render_shell = make_shell_renderer(
        ...     "partials/nav.html",
        ...     context_builder=build_nav_context,
        ... )
        >>> 
        >>> # In a view
        >>> return render_shell(
        ...     request,
        ...     "project/detail.html",
        ...     {"project": project},
        ...     extra_oob=[Oob("partials/notifications.html", target_id="alerts")],
        ... )
        >>> 
        >>> # This always includes the nav as an OOB, plus any extra OOBs
    """
    def render_shell(request, template_name, context=None, *, extra_oob=(), **kwargs):
        context = dict(context or {})
        if context_builder is not None:
            context.update(context_builder(request))
        shell_oob = Oob(shell_template, context)
        return render_htmx(request, template_name, context, oobs=(shell_oob, *extra_oob), **kwargs)
    return render_shell
