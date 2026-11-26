+++
title = "Solving Stale Navigation in Hypermedia Applications · Architectural Guide"
meta_description = "An in-depth architectural guide on solving state drift and stale navigation in server-driven hypermedia apps. Compares Turbo, LiveView, Unpoly, and Django with HTMX."
eyebrow = "Comprehensive Architectural Guide"
heading = "Solving Stale Navigation in Hypermedia Applications"
lede = "When transitioning from classic multi-page apps to HTML-over-the-wire, partial container swaps often cause **state drift** across breadcrumbs, sidebars, and application chrome. Here are shown how to approach the problem and the trade-offs of each strategy."
demo_variant = "htmx_nav_declarative"
+++

## 1. The Stale Navigation Problem (State Drift) {#the-problem}

When developers begin using HTMX to accelerate navigation in a server-rendered application, the instinctive first step is to target the center content container:

```html
<!-- Naive approach: Swapping only the inner container -->
<a href="/projects/42/board/"
   hx-get="/projects/42/board/"
   hx-target="#main-content"
   hx-push-url="true">
  Kanban Board
</a>
```

While this updates `#main-content` smoothly without a full page refresh, it creates a subtle, jarring failure mode known as **State Drift**:

| Stale Navigation (Bug) | Synchronized Navigation (Goal) |
| :--- | :--- |
| Sidebar and breadcrumbs show previous state. | Sidebar, breadcrumbs, and title update out-of-band simultaneously. |
| Document `<title>` does not update automatically. | Direct page refresh produces the identical visual tree (URL as source of truth). |

Single-Page Applications (SPAs) avoid this by maintaining a centralized client-side state tree, at the cost of client-server API contracts, state synchronization bugs, and heavy JavaScript runtimes. The goal of server-driven hypermedia is to solve this *without* abandoning the server as the single source of truth.

## 2. The Landscape of General Solutions {#general-methods}

Across the web development ecosystem, several architectural strategies have emerged to address multi-region navigation updates.

### 2.1 Full Render + Client Slicing or DOM Morphing (Idiomorph) {#method-full-render}

The server renders the complete HTML document on every navigation request. The client then extracts fragments with `hx-select` / `hx-select-oob` or diffs the incoming DOM against the live DOM with **Idiomorph**.

```html
<!-- Client-side extraction: pull only what changed out of a full-page response -->
<a hx-get="/projects/42/board/"
   hx-target="#main-content"
   hx-select="#main-content"
   hx-select-oob="#sidebar,#breadcrumbs">
  Kanban Board
</a>
```

```html
<!-- Client-side morphing on boosted body -->
<body hx-boost="true" hx-swap="morph:innerHTML">
  <!-- Server returns full layout; client diffs and updates mutated nodes -->
</body>
```

- **Advantages:** Zero view-layer changes on the backend; preserves form focus, input state, and scroll positions when morphing.
- **Trade-offs:** Highest wire payload and server strain (sends full layout HTML every click); region lists live in markup attributes (mistyped IDs fail quietly); DOM diffing costs client CPU cycles on large documents.

### 2.2 Pinpoint Swaps via Template Logic (Hand written OOB) {#method-template-oob}

The template layer inspects whether the request came from HTMX (e.g. via `django-htmx` middleware) and conditionally includes out-of-band (OOB) containers.

```django
<!-- Manual branching inside Django templates -->
{% extends request.htmx|yesno:"empty.html,base.html" %}
{% block content %}
  {% if request.htmx %}
    <div id="sidebar" hx-swap-oob="innerHTML">{% include "components/_sidebar.html" %}</div>
    <div id="breadcrumbs" hx-swap-oob="innerHTML">{% include "components/_breadcrumbs.html" %}</div>
  {% endif %}
  <!-- Page content goes here... -->
{% endblock %}
```

- **Advantages:** Reduced wire payload compared to full-document rendering; targeted DOM replacements require no morphing.
- **Trade-offs:** Page templates carry `request.htmx` checks and `hx-swap-oob` wrappers; `HX-Target` branching leaks into markup per nesting level; typos in target IDs or missing middleware fail silently.

### 2.3 Pinpoint Swaps via Backend Orchestration {#method-backend-oob}

Views detect HTMX requests and assemble a multi-part response in Python, joining the primary partial with OOB swap strings.

```python
# Ad-hoc backend string concatenation in Django views
def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    ctx = {"project": project, "tickets": project.tickets.all()}

    if request.headers.get("HX-Request"):
        content = render_to_string("pages/board_partial.html", ctx, request=request)
        sidebar = render_to_string("components/_sidebar.html", ctx, request=request)
        oob = f'<div id="sidebar" hx-swap-oob="innerHTML">{sidebar}</div>'
        return HttpResponse(content + oob)

    return render(request, "pages/board.html", ctx)
```

- **Advantages:** Templates stay clean of HTMX-specific branching and transport wrappers; fine-grained programmatic control over which regions swap.
- **Trade-offs:** Brittle manual string concatenation; state drift by omission when views forget breadcrumbs, title, or sidebar swaps; repeated header checks per view.

> A middleware that inspects every response and appends the same OOB fragments automatically trades per-view locality for less boilerplate, without changing the underlying push-based sync model.

### 2.4 Event-Driven Sync (HX-Trigger + Client Re-fetch) {#method-event-driven}

Instead of pushing secondary regions from the primary view, the primary response fires an event via `HX-Trigger`, and listening regions independently re-fetch themselves.

```python
# The primary view has no knowledge of the sidebar or breadcrumbs at all
def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    response = render(request, "pages/board_partial.html", {"project": project})
    response["HX-Trigger"] = "nav-changed"
    return response
```

```html
<div id="sidebar" hx-get="/nav/sidebar/" hx-trigger="nav-changed from:body">...</div>
<div id="breadcrumbs" hx-get="/nav/breadcrumbs/" hx-trigger="nav-changed from:body">...</div>
```

- **Advantages:** Primary view stays decoupled from secondary regions; well suited to cross-cutting badges and unread counters.
- **Trade-offs:** Adds an extra round trip and N times the per-request server overhead; regions update asynchronously and can drift if one fetch fails; secondary endpoints must infer route context from URLs or event data.

### 2.5 Template Substitution (Dispatch Before Render) {#method-template-substitution}

Swaps the *entire template* before rendering based on a single request header, then calls Django's normal `render()` unmodified.

```python
def get_template(request: HttpRequest, template_name: str) -> str:
    """Substitutes a full template for its OOB shell on HTMX requests."""
    if request.headers.get("HX-Request", "") == "true":
        name = template_name.rsplit("/", 1)[-1]
        return f"vanilla_htmx_composite/_{name}"
    return template_name
```

- **Advantages:** No conditional branching inside templates; no manual OOB string-joining in views; preserves standard `render()` signatures.
- **Trade-offs:** Companion `_{name}.html` shadow templates must be maintained for every page and still embed `hx-swap-oob` attributes; handles only one `HX-Target` per dispatch check.

See `get_template()` applied to the full `overview` view in [Section 4.2](#code-vanilla).

### 2.6 Native Template Partials (Django 6.0+) {#method-native-partials}

Django 6.0 native template partials allow defining reusable inline fragments inside a single template using `{% partialdef %}` tags. This is a **complementary primitive**, not a sync strategy: it removes shadow files, while still requiring a dispatch mechanism and OOB sync for outer regions.

```django
{% extends 'base.html' %}
{% block content %}
{% partialdef content inline %}
  <div>Page content</div>
{% endpartialdef %}
{% endblock %}
```

```python
# Template substitution (section 2.5), retargeted at a named partial
def get_template(request, template_name: str) -> str:
    if request.headers.get("HX-Request") == "true":
        return f"{template_name}#content"
    return template_name
```

- **Advantages:** Single-file locality without duplicated page content; composes with backend orchestration ([2.3](#method-backend-oob)) or template dispatch ([2.5](#method-template-substitution)).
- **Trade-offs:** A partial alone still leaves the sidebar and breadcrumbs stale; requires consistent partial naming and a dispatch layer.

## 3. The django-htmx-nav Architecture {#django-htmx-nav-model}

Two small primitives: `render_nav` decides *what the main response is*, and `Swap` decides *what else rides along*.

`render_nav` returns the full page on a direct visit, or the matching `partialdef` block on an HTMX request. `Swap` carries the sidebar, breadcrumbs, and counters that live outside that partial as frozen Python dataclasses decoupled from both template markup and view routing.

### 3.1 `render_nav`: One Render Call, Two Response Shapes {#render_nav}

`render_nav` is a drop-in replacement for `render()` that selects the full page or named partial from the request:

```python
# views.py
from django.shortcuts import get_object_or_404
from htmx_nav import render_nav


def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Full page on direct visits, partial on HTMX
    return render_nav(request, "pages/board.html", {"project": project})
```

```django
{# pages/board.html #}
{% extends "base.html" %}

{% block content %}
{% partialdef content inline %}
  <div id="content">
    ...
  </div>
{% endpartialdef %}
{% endblock %}
```

What `render_nav` adds beyond a bare `get_template()` helper:

- Sets `Vary: HX-Request` automatically so caches never serve a fragment as a full page.
- `partial=` accepts a block name, template path, callable, or dict mapping partials to `HX-Target` conditions.
- `title=` populates `context["title"]` on full renders and appends an escaped `<title>` on HTMX renders.
- `swaps=` attaches companion `Swap` fragments to sync every other region.

> **Note:** With `render_nav` alone, content swaps cleanly but outer chrome stays stale—that is what `Swap` closes next.

### 3.2 The `Swap` Primitive & Zero-Boilerplate Auto-Wrapping {#swap-auto-wrap}

Instead of duplicating templates into OOB variants or polluting reusable components with `hx-swap-oob` wrappers, `Swap` wraps standard component templates at render time:

```django
{# _sidebar.html — clean, standard HTML partial: reusable in {% include %} or OOB #}
<ul class="menu p-4">
  <li class="menu-title">Projects</li>
  {% for proj in projects %}
    <li><a href="{{ proj.url }}">{{ proj.name }}</a></li>
  {% endfor %}
</ul>
```

```html
<!-- Wire output generated by Swap(..., target_id="sidebar") -->
<div id="sidebar" hx-swap-oob="innerHTML">
  <ul class="menu p-4">
    <li class="menu-title">Projects</li>
    ...
  </ul>
</div>
```

For HTMX v4, setting `wrap="hx-partial"` emits `<hx-partial hx-target="#sidebar" hx-swap="innerHTML">` instead.

### 3.3 Python-First Versatility: Direct FBVs, Reusable Shells, and CBV Mixins {#swap-orchestration}

Because `Swap` is a regular Python object, it composes across three progressive levels:

**1. Direct FBVs (`render_nav` + `Swap`)** — list swaps explicitly per endpoint:

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, render_nav


def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    return render_nav(
        request,
        "pages/board.html",
        {"project": project},
        swaps=[
            Swap(
                "components/_sidebar.html", {"user": request.user}, target_id="sidebar"
            ),
            Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
        ],
        title=project.name,
    )
```

**2. Reusable Shells (`make_shell_renderer`)** — declare recurring shell fragments once and add `extra_swaps` per view:

```python
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, make_shell_renderer

render_shell = make_shell_renderer(
    lambda request: [
        Swap("components/_sidebar.html", {"user": request.user}, target_id="sidebar"),
        Swap("components/_breadcrumbs.html", target_id="breadcrumbs"),
    ]
)


def project_board(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return render_shell(
        request,
        "pages/board.html",
        {"project": project},
        extra_swaps=Swap("components/_status_badge.html", target_id="project-status"),
    )
```

**3. Class-Based Views (`make_shell_view_mixin`)** — reuse the same shell inside `ListView` / `DetailView`:

```python
from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin

ShellViewMixin = make_shell_view_mixin(render_shell)


class ProjectBoardView(ShellViewMixin, DetailView):
    model = Project
    template_name = "pages/board.html"
    context_object_name = "project"

    def get_extra_swaps(self):
        return Swap("components/_status_badge.html", target_id="project-status")
```

### 3.4 First-Class Support for Text, Deletion, and Flash Messages {#swap-specialized}

Specialized `Swap` helpers avoid template overhead for counters, deletions, and `django.contrib.messages`:

- `Swap.text("unread-count", "7")`: sends raw string or numeric content without touching the template engine.
- `Swap.delete("flash-notification")`: emits `hx-swap-oob="delete"` for modals, alerts, or removed table rows.
- `Swap("...", include_if=has_messages)`: suppresses the message swap automatically when no flash messages are pending.

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404
from htmx_nav import Swap, has_messages, render_nav


def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    messages.success(request, f"Ticket #{ticket_id} deleted.")

    return render_nav(
        request,
        "tickets/empty_state.html",
        partial=None,
        swaps=[
            Swap.delete(f"ticket-row-{ticket_id}"),
            Swap.text(
                "open-tickets-count", str(Ticket.objects.filter(status="open").count())
            ),
            Swap(
                "components/_messages.html",
                target_id="messages",
                include_if=has_messages,
            ),
        ],
    )
```

### 3.5 Pythonic Targeting: One Vocabulary for Partials and Swaps {#swap-targeting}

Instead of writing `{% if request.htmx and request.headers.HX_Target == "tab-content" %}` in templates, both `partial=` and `include_if=` share one Python condition vocabulary (DOM ID strings, `targeting()` / `not_targeting()` predicates, callables, or booleans) evaluated before templates are parsed:

```python
from htmx_nav import Swap, render_nav, targeting


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        partial={
            "#tab_content": targeting("tab-content"),
            "#content": True,  # fallback for any other HTMX request
        },
        swaps=[
            Swap(
                "nav/_tabs.html", target_id="tabs", include_if=targeting("tab-content")
            ),
        ],
    )
```

Individual swaps support the same predicates via `include_if`:

```python
from htmx_nav import Swap, has_messages, not_targeting, targeting

swaps = [
    Swap("nav/_tabs.html", include_if="tab-content"),
    Swap("nav/_breadcrumbs.html", include_if=targeting("main-content", "subtabs")),
    Swap("nav/_sidebar.html", include_if=not_targeting("sidebar")),
    Swap("nav/_messages.html", include_if=has_messages),
    Swap("nav/_admin_badge.html", include_if=lambda req: req.user.is_staff),
]
```

### 3.6 Built-in Visual Swap Debugging {#swap-debugging}

Enable visual swap pulse highlights in settings (or via `?debug-swaps=1` in the live demo) to confirm which DOM targets update on every click:

```python
# settings.py
HTMX_NAV_DEBUG_SWAPS = True
```

[See it in action in the live demo]({{ DEMO_URL }}{% url 'demo_entry' 'htmx_nav_declarative' 'project_settings' %}?debug-swaps=1).

## 4. Code Walkthrough by Implementation Variant {#example-variants}

The example project implements the same Helpdesk application across several architectures. Each variant below shares these context helpers:

```python
from django.http import HttpRequest, HttpResponse

from core.models import Organization, Project


def _sidebar_context(
    active_org_id: str | None = None,
    active_project_id: str | None = None,
    active_page: str | None = None,
):
    orgs = Organization.objects.prefetch_related("projects").only("id", "name")
    return {
        "orgs": orgs,
        "active_org_id": active_org_id,
        "active_project_id": active_project_id,
        "active_page": active_page,
    }


def _breadcrumbs(*crumbs: tuple[str, str | None]):
    return {"breadcrumbs": [{"label": label, "url": url} for label, url in crumbs]}
```

### 4.1 Pure Multi-Page Application {#code-mpa}

Each navigation request renders the complete document and replaces the current page. ([Try Live MPA Demo]({{ DEMO_URL }}{% url 'demo_entry' 'mpa' %}) · [View on GitHub](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/mpa/views.py))

```python
# example/mpa/views.py
from django.shortcuts import render


def overview(request: HttpRequest) -> HttpResponse:
    """Classic Django full-page rendering."""
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("Helpdesk", None)),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render(request, "core/pages/overview.html", context)
```

> **Trade-off:** Straightforward implementation, but every navigation returns the complete page (~6.1 KB wire payload per click).

### 4.2 Vanilla HTMX + Shell Templates {#code-vanilla}

Reduces the response to the updated content plus OOB regions, at the cost of maintaining parallel `_*.html` shell templates. ([Try Live Vanilla Demo]({{ DEMO_URL }}{% url 'demo_entry' 'vanilla_htmx_composite' %}) · [View on GitHub](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/vanilla_htmx_composite/views.py))

```python
# example/vanilla_htmx_composite/views.py
from django.shortcuts import render


def get_template(request: HttpRequest, template_name: str) -> str:
    """Substitutes a full template for its OOB shell on HTMX requests."""
    if request.headers.get("HX-Request", "") == "true":
        name = template_name.rsplit("/", 1)[-1]
        return f"vanilla_htmx_composite/_{name}"
    return template_name


def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("Helpdesk", None)),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    template = get_template(request, "core/pages/overview.html")
    return render(request, template, context)
```

```django
{# templates/vanilla_htmx_composite/_overview.html #}
<div id="sidebar" hx-swap-oob="innerHTML">{% include "core/components/_sidebar_menu.html" %}</div>
<div id="breadcrumbs" hx-swap-oob="innerHTML">{% include "core/components/_breadcrumbs.html" %}</div>
{% include "core/pages/overview.html#content" %}
```

> **Trade-off:** Drops payload by ~{{ bench.payload_reduction_pct }}% to **~{{ bench.payload_value }}**, but requires maintaining a parallel `_*.html` shell template.

### 4.3 Composite Swaps {#code-htmx-nav-composite}

Describes secondary navigation regions directly in the view as `Swap` objects without parallel shell templates. ([Try Live Composite Demo]({{ DEMO_URL }}{% url 'demo_entry' 'htmx_nav_composite' %}) · [View on GitHub](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/htmx_nav_demo/views_composite.py))

```python
# example/htmx_nav_demo/views_composite.py
from htmx_nav import Swap, render_nav


def _sidebar_swap(active_page: str | None = None) -> Swap:
    return Swap(
        "core/components/_sidebar_menu.html",
        _sidebar_context(active_page),
        target_id="sidebar",
    )


def _breadcrumb_swap(*crumbs: tuple[str, str | None]) -> Swap:
    return Swap(
        "core/components/_breadcrumbs.html",
        _breadcrumbs(*crumbs),
        target_id="breadcrumbs",
    )


def overview(request: HttpRequest) -> HttpResponse:
    """Display the main helpdesk overview dashboard."""
    context = {
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_nav(
        request,
        "core/pages/overview.html",
        context,
        swaps=[
            _sidebar_swap(active_page="overview"),
            _breadcrumb_swap(("helpdesk", None)),
        ],
    )
```

> **Trade-off:** Same ~{{ bench.payload_reduction_pct }}% payload reduction (~{{ bench.payload_value }}), while keeping navigation fragments independent from the page template.

### 4.4 Shared Shell Renderer {#code-htmx-nav-baseline}

Moves the repeated `Swap` configuration out of individual views so views look like standard Django views. ([Try Live Baseline Demo]({{ DEMO_URL }}{% url 'demo_entry' 'htmx_nav_baseline' %}) · [View on GitHub](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/htmx_nav_demo/views_baseline.py))

```python
# example/htmx_nav_demo/views_baseline.py
from htmx_nav import Swap, make_shell_renderer

render_shell = make_shell_renderer(
    [
        Swap("core/components/_sidebar_menu.html", target_id="sidebar"),
        Swap("core/components/_breadcrumbs.html", target_id="breadcrumbs"),
    ]
)


def overview(request: HttpRequest) -> HttpResponse:
    context = {
        **_sidebar_context(active_page="overview"),
        **_breadcrumbs(("Helpdesk", None)),
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_shell(request, "core/pages/overview.html", context)
```

> **Trade-off:** Centralizes navigation shell behavior while keeping normal Django view structure.

### 4.5 Declarative Navigation Registry {#code-htmx-nav-declarative}

Moves route-specific navigation metadata into a central registry so views only fetch their own domain data. ([Try Live Declarative Demo]({{ DEMO_URL }}{% url 'demo_entry' 'htmx_nav_declarative' %}) · [View on GitHub](https://github.com/lucas-rollin/django-htmx-nav/blob/main/example/htmx_nav_demo/views_declarative.py))

```python
# example/htmx_nav_demo/registry_declarative.py
from htmx_nav import Swap, make_shell_renderer

NAV_ENTRIES: dict = {
    "overview": {
        "active_page": "overview",
        "breadcrumbs": [("Helpdesk", None)],
    },
    # Other entries...
}


def _sidebar_ctx(request: HttpRequest) -> dict:
    entry = NAV_ENTRIES.get(request.resolver_match.url_name, {})
    return _sidebar_context(active_page=entry.get("active_page", ""))


def _breadcrumbs_ctx(request: HttpRequest) -> dict:
    entry = NAV_ENTRIES.get(request.resolver_match.url_name, {})
    return _breadcrumbs(entry.get("breadcrumbs", []))


def build_shell_swaps(request: HttpRequest) -> list[Swap]:
    return [
        Swap(
            "core/components/_sidebar_menu.html",
            _sidebar_ctx(request),
            target_id="sidebar",
        ),
        Swap(
            "core/components/_breadcrumbs.html",
            _breadcrumbs_ctx(request),
            target_id="breadcrumbs",
        ),
    ]


render_shell = make_shell_renderer(build_shell_swaps)
```

```python
# example/htmx_nav_demo/views_declarative.py
from .registry_declarative import render_shell


def overview(request: HttpRequest) -> HttpResponse:
    context = {
        "org_count": Organization.objects.count(),
        "project_count": Project.objects.count(),
    }
    return render_shell(request, "core/pages/overview.html", context)
```

> **Trade-off:** Centralizes route-driven navigation metadata; views contain no breadcrumb or sidebar configuration.

### 4.6 Orthogonal Client-Side Axes {#code-orthogonal-axes}

These client-side enhancements are independent of the server architecture and combine with any variant above:

- **+HS (`hx-select-oob`)**: selects secondary regions from a response when the backend does not provide them as OOB swaps (useful for incremental migration).
- **+M (Idiomorph)**: replaces standard `innerHTML` swaps with DOM morphing to preserve input focus and minimize DOM replacement.

## 5. Empirical Benchmark Findings {#benchmarks-findings}

Data collected from automated Playwright test runs and Django query counters across the Helpdesk reference testbed:

<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 not-prose my-6">
  {% include "frontpage/components/_stat_card.html" with label="Average Payload" tone="primary" value=bench.payload_value desc=bench.payload_desc desc_highlight=True %}
  {% include "frontpage/components/_stat_card.html" with label="Render Latency" tone="secondary" value=bench.render_latency_value desc="Negligible swap construction cost" %}
  {% include "frontpage/components/_stat_card.html" with label="Database Queries" tone="base-content" value=bench.db_queries_value desc="0 query duplication with cache" desc_highlight=True %}
</div>

Explore interactive charts, ranked variants, and payload distributions in the [Benchmarks Dashboard]({% url 'benchmarks:overview' %}).

## 6. Architectural Decision Tree {#decision-tree}

Use this guide to choose the navigation strategy that best fits your Django project:

<div class="space-y-4 not-prose my-6 text-sm">
  <!-- Tier 1 -->
  <div class="collapse collapse-arrow bg-base-200/50 border border-base-300 rounded-xl">
    <input type="radio" name="decision-accordion" checked="checked">
    <div class="collapse-title font-bold flex items-center gap-2">
      <span class="badge badge-soft badge-sm font-mono">1</span>
      Simple marketing sites, blogs, or mostly static documents
    </div>
    <div class="collapse-content text-xs text-base-content/80 leading-relaxed">
      <p>
        <span class="badge badge-neutral badge-sm align-middle">MPA</span>
        <strong class="ml-1">Recommendation:</strong>
        Use <strong>Pure MPA</strong>, or add plain <code>hx-boost="true"</code> to
        <code>&lt;body&gt;</code> for progressively enhanced navigation.
      </p>
      <p class="mt-1">
        Without complex nested dashboards or dynamic layout controls, the simplicity
        of traditional full-page rendering outweighs the benefits of partial navigation.
      </p>
    </div>
  </div>
  <!-- Tier 2 -->
  <div class="collapse collapse-arrow bg-base-200/50 border border-base-300 rounded-xl">
    <input type="radio" name="decision-accordion">
    <div class="collapse-title font-bold flex items-center gap-2">
      <span class="badge badge-soft badge-sm font-mono">2</span>
      Small SaaS apps with 1-2 layout regions (e.g. fixed sidebar, 1 tab bar)
    </div>
    <div class="collapse-content text-xs text-base-content/80 leading-relaxed">
      <p>
        <span class="badge badge-primary badge-sm align-middle">django-htmx-nav</span>
        <strong class="ml-1">Recommendation:</strong>
        Use the <a href="#code-htmx-nav-baseline" class="link link-primary font-semibold">Shared Shell Renderer</a>
        pattern (<code>make_shell_renderer</code>).
      </p>
      <p class="mt-1">
        Define your 2-3 standard layout swaps once and reuse <code>render_shell</code>
        in place of <code>render()</code>. Views stay standard Django views, with no
        parallel directory of shell templates to maintain.
      </p>
      <div class="mt-3 pt-2 border-t border-base-300/70">
        <p>
          <span class="badge badge-secondary badge-sm align-middle">Vanilla HTMX</span>
          <strong class="ml-1">Alternative:</strong>
          Prefer no extra dependency? The
          <a href="#code-vanilla" class="link link-secondary font-semibold">Vanilla HTMX &amp; Shell Templates</a>
          pattern works well here.
        </p>
        <p class="mt-1">
          With only one HX-Target to branch on, <code>get_template()</code> can swap in the
          right shell partial in a single line. The conditional stays contained and
          never needs to leak into templates or balloon the view.
        </p>
      </div>
    </div>
  </div>
  <!-- Tier 3 -->
  <div class="collapse collapse-arrow bg-base-200/50 border border-base-300 rounded-xl">
    <input type="radio" name="decision-accordion">
    <div class="collapse-title font-bold flex items-center gap-2">
      <span class="badge badge-soft badge-sm font-mono">3</span>
      Complex web apps with deep nesting (organizations, projects, subtabs, wizard steps)
    </div>
    <div class="collapse-content text-xs text-base-content/80 leading-relaxed">
      <p>
        <span class="badge badge-primary badge-sm align-middle">django-htmx-nav</span>
        <strong class="ml-1">Recommendation:</strong>
        Use the <a href="#code-htmx-nav-declarative" class="link link-primary font-semibold">Declarative Navigation Registry</a> with <code>cache_on_request</code>.
      </p>
      <p class="mt-1">
        A central navigation registry keeps views focused on application logic.
        With <code>cache_on_request</code>, resolved navigation state can be reused
        across components within the same request instead of being resolved repeatedly.
      </p>
      <div class="mt-3 pt-2 border-t border-base-300/70">
        <p>
          <span class="badge badge-primary badge-sm align-middle">django-htmx-nav</span>
          <strong class="ml-1">Alternative:</strong>
          Want no registry overhead? Extend the
          <a href="#code-htmx-nav-baseline" class="link link-primary font-semibold">Shared Shell Renderer</a>
          or <a href="#code-htmx-nav-composite" class="link link-primary font-semibold">Composite Swaps</a>
          pattern to cover every region.
        </p>
        <p class="mt-1">
          This skips the registry's route-metadata layer at the cost of listing
          every <code>Swap</code> explicitly per view (or per shell) rather than deriving it
          from the current route.
        </p>
      </div>
      <div class="mt-3 pt-2 border-t border-base-300/70">
        <p>
          <span class="badge badge-secondary badge-sm align-middle">Vanilla HTMX</span>
          <strong class="ml-1">Alternative:</strong>
          The equivalent atomic-OOB vanilla approach
          <a href="https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/vanilla_htmx_atomic"
             target="_blank"
             rel="noopener noreferrer"
             class="link link-secondary font-semibold inline-flex items-center gap-1">
            (view source
            {% include "frontpage/components/_arrow_icon.html" with size="3" %})
          </a>
          can still get you there without the dependency.
        </p>
        <p class="mt-1">
          The trade-off scales with nesting depth: every additional decision point
          (org → project → subtab/wizard) means either more branching inside templates
          (Section 2.2) or more repeated OOB assembly across views (Section 2.3).
        </p>
      </div>
    </div>
  </div>
</div>
