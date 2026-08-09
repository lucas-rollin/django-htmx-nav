from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.cache import patch_vary_headers
from django.utils.html import escape

TITLE_CONTEXT_KEY = getattr(settings, "HTMX_NAV_TITLE_CONTEXT_KEY", "title")


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
        include_if: Optional predicate deciding whether this Swap applies to
            a given request. Use this for nested layouts where a fragment
            should be skipped when an ancestor's own re-render already
            covers it — see `skip_if_target_in`.
    """

    template_name: str
    context: dict[str, Any] | None = None
    target_id: str | None = None
    include_if: Callable[[HttpRequest], bool] | None = None

    def applies_to(self, request: HttpRequest) -> bool:
        """Whether this swap should render for the given request. Defaults
        to always applying when `include_if` is not set."""
        if self.include_if is None:
            return True
        return self.include_if(request)

    def render(
        self, 
        request: HttpRequest, 
        parent_context: dict[str, Any] | None = None,
        using: str | None = None
    ) -> str:
        """
        Render this swap fragment, OOB-wrapping it if `target_id` is set.
        
        Swap's own context takes precedence for its specific fragment,
        but inherits all global page variables from parent_context.
        """
        final_context = {**(parent_context or {}), **(self.context or {})}

        html = render_to_string(
            self.template_name, final_context, request=request, using=using
        )
        if self.target_id:
            html = f'<div id="{self.target_id}" hx-swap-oob="innerHTML">{html}</div>'
        return html


def _normalize_swaps(swaps: "Swap | list[Swap] | None") -> list[Swap]:
    """Normalize a single Swap, a list of Swaps, or None into a list."""
    if swaps is None:
        return []
    if isinstance(swaps, Swap):
        return [swaps]
    return list(swaps)


def _htmx_target_is(target: str | None, dom_id: str) -> bool:
    """Match a raw HX-Target header value against a bare DOM id."""
    if not target:
        return False
    return target == dom_id or target == f"#{dom_id}" or target.endswith(f"#{dom_id}")


def htmx_target_is(request: HttpRequest, *dom_ids: str) -> bool:
    """
    Return True if the request's HX-Target matches one of the given DOM ids.

    Works with or without django-htmx installed (falls back to `None` if
    `request.htmx` isn't present, which never matches).

    Useful in view code that needs to choose a `partial_name` based on which
    element htmx is targeting, e.g.:

        partial_name = "content" if htmx_target_is(request, "page-content") else "tab_content"
    """
    htmx = getattr(request, "htmx", None)
    target = getattr(htmx, "target", None) if htmx else None
    return any(_htmx_target_is(target, dom_id) for dom_id in dom_ids)


def skip_if_target_in(*dom_ids: str) -> Callable[[HttpRequest], bool]:
    """
    Build an `include_if` predicate for a `Swap`.

    The predicate excludes the swap when the request's `HX-Target` matches
    one of the given DOM IDs, since that target's own re-render already
    includes this component inline and an OOB update would be redundant.

    Args:
        *dom_ids: DOM IDs whose targets should cause the swap to be skipped.

    Returns:
        A predicate that accepts an HTTP request and returns whether the
        swap should be included.
    """

    def predicate(request: HttpRequest) -> bool:
        return not htmx_target_is(request, *dom_ids)

    return predicate


def _resolve_partial(
    template_name: str, partial_name: str | None, is_htmx: bool
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
    context: dict[str, Any] | None = None,
    content_type: str | None = None,
    status: int | None = None,
    using: str | None = None,
    *,
    partial_name: str | None = "content",
    swaps: Swap | list[Swap] | None = None,
    title: str | None = None,
) -> TemplateResponse:
    """
    Render a template with HTMX-aware partial and swap support.

    On HTMX requests, it renders only the specified partial (using Django's
    `template.html#partial` syntax) and appends any swap fragments (out-of-band
    or hx-partial fragments) whose `include_if` predicate (if any) passes for
    this request. On regular requests, it renders the full template.

    Args:
        request: The Django HTTP request.
        template_name: Base template name to render.
        context: Optional template context dictionary.
        content_type: Optional content type for the response.
        status: Optional HTTP status code.
        using: Optional template engine name to use.
        partial_name: Name of the django partial to render on HTMX requests.
            Defaults to "content". Set to None to disable partial rendering.
        swaps: A Swap, a list of Swaps, or None. Appended on HTMX requests.
        title: Optional page title. Added to the context under
            `TITLE_CONTEXT_KEY` (default `"title"`, overridable via the
            `HTMX_NAV_TITLE_CONTEXT_KEY` setting). Always wins over a
            same-named key already in `context`. On HTMX requests it's also
            appended as a bare `<title>` tag, which htmx picks up
            automatically to update `document.title`.

    Returns:
        TemplateResponse configured for HTMX or regular rendering.

    Raises:
        TemplateDoesNotExist: If the template or partial cannot be found.

    Example:
        .. code-block:: python

            # Basic usage
            return render_htmx(request, "project/detail.html", {"project": project})

            # With swap fragments (a single Swap or a list both work)
            return render_htmx(
                request,
                "project/detail.html",
                {"project": project},
                swaps=[
                    Swap("partials/nav.html", {"active": "projects"}, target_id="nav"),
                    Swap("partials/notifications.html", target_id="alerts"),
                ],
                title=project.name,
            )
    """
    is_htmx = _is_htmx_request(request)
    swap_list = _normalize_swaps(swaps)
    
    page_context = dict(context or {})

    # Feed Swap contexts into page_context for Full Page reloads
    merged_swap_context: dict[str, Any] = {}
    for swap in swap_list:
        if swap.context:
            merged_swap_context.update(swap.context)

    page_context = {**merged_swap_context, **page_context}

    page_context.setdefault("active_partial", partial_name)
    page_context.setdefault(TITLE_CONTEXT_KEY, None)

    if title is not None:
        page_context[TITLE_CONTEXT_KEY] = title

    effective_title = page_context.get(TITLE_CONTEXT_KEY)
    resolved_template = _resolve_partial(template_name, partial_name, is_htmx)
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

        def append_swap(resp):
            for swap in swap_list:
                if not swap.applies_to(request):
                    continue
                # Pass page_context so swaps inherit request-wide variables
                swap_html = swap.render(request, parent_context=page_context, using=using)
                resp.content += swap_html.encode(resp.charset)

            if effective_title:
                resp.content += f"<title>{escape(effective_title)}</title>".encode(
                    resp.charset
                )
            return resp

        response.add_post_render_callback(append_swap)
    return response


class ShellRenderer(Protocol):
    def __call__(
        self,
        request: HttpRequest,
        template_name: str,
        context: dict[str, Any] | None = None,
        *,
        extra_swaps: Swap | list[Swap] | None = None,
        partial_name: str | None = "content",
        **kwargs: Any,
    ) -> TemplateResponse: ...


def make_shell_renderer(
    shell_template: str,
    context_builder: Callable[[HttpRequest], dict[str, Any]] | None = None,
    *,
    target_id: str | None = None,
    include_if: Callable[[HttpRequest], bool] | None = None,
    namespace: str | None = None,
) -> ShellRenderer:
    """
    Creates a wrapper function of `render_htmx` that with fixed shell fragment.

    Factory for a `render_shell` function: a thin wrapper around `render_htmx`
    that always includes a fixed shell fragment (e.g. nav, breadcrumbs) built
    from `context_builder`, on top of whatever else the caller passes.

    Args:
        shell_template: Template path for the shell fragment (e.g. "partials/nav.html").
        context_builder: Optional callable building shell-only context.
        target_id: Optional DOM id to OOB-wrap the shell fragment with.
        include_if: Optional predicate deciding whether the shell fragment
            itself renders for a given request.
        namespace: Optional dict key to namespace shell context variables under.
            If None (default), shell context is merged flatly into the page
            context, with page-supplied values always winning on key collisions
            (for both the page context and what the shell fragment sees).

    Returns:
        A `render_shell` function with the same call signature as `render_htmx`
        (minus `template_name`/`context` handling), plus `extra_swaps`.

    Example:
        .. code-block:: python

            render_page = make_shell_renderer(
                "partials/nav.html",
                context_builder=lambda r: {"user": r.user},
            )

            response = render_page(
                request,
                "project/detail.html",
                {"project": project},
                partial_name="tab_content",  # picked explicitly by the caller
            )
    """

    def render_shell(
        request: HttpRequest,
        template_name: str,
        context: dict[str, Any] | None = None,
        *,
        extra_swaps: Swap | list[Swap] | None = None,
        partial_name: str | None = "content",
        **kwargs: Any,
    ) -> TemplateResponse:
        page_context = dict(context or {})
        shell_context = context_builder(request) if context_builder is not None else {}

        if namespace is not None:
            swap_ctx = {namespace: shell_context}
        else:
            swap_ctx = shell_context

        shell_swap = Swap(
            shell_template,
            context=swap_ctx,
            target_id=target_id,
            include_if=include_if,
        )

        return render_htmx(
            request,
            template_name,
            page_context,
            partial_name=partial_name,
            swaps=[shell_swap, *_normalize_swaps(extra_swaps)],
            **kwargs,
        )

    return render_shell
