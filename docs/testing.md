# Testing

`django-htmx-nav` provides automated test utilities to verify navigation state consistency across HTMX request pathways.

## 1. Verifying Navigation Parity (`assert_shell_parity`)

In applications using shell layouts (sidebars, breadcrumbs, headers), a single page URL can often be reached in multiple ways:

1. **Full Page Reload:** Initial browser navigation or page refresh.
2. **Page Shell Swap:** HTMX navigation into the page targeting the main container.
3. **Tab/Component Swap:** HTMX interaction within the page targeting a partial container.

`assert_shell_parity` makes HTTP requests for each pathway using Django's test client and asserts that the resolved template context yields identical navigation data across all variants.

```python
from django.test import Client
from htmx_nav.testing import assert_shell_parity


def test_project_detail_navigation_parity(client: Client, project):
    assert_shell_parity(
        client,
        f"/projects/{project.pk}/",
        requests={
            "full_reload": {},
            "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
            "tab_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
        },
        checks={
            "sidebar_active_item": lambda ctx: [
                item["label"] for item in ctx["nav"]["sidebar"] if item["active"]
            ],
            "breadcrumbs": lambda ctx: [c["label"] for c in ctx["nav"]["breadcrumbs"]],
            "active_partial": lambda ctx: ctx.get("active_partial"),
        },
    )
```

## 2. Verifying DOM Fragment Composition (`assert_shell_composition`)

While `assert_shell_parity` verifies template context parity, `assert_shell_composition` goes further by parsing the actual response HTML using BeautifulSoup to ensure that:

1. The full-reload response's `#page-content` fragment matches the page-shell response body.
2. The page-shell response's `#tab-content` fragment matches the tab-shell response body.
3. The full-reload response's `#tab-content` fragment matches the tab-shell response body.

This catches bugs such as missing wrapper elements or header-dependent template branching that context assertions alone cannot detect.

```python
from django.test import Client
from htmx_nav.testing import assert_shell_composition


def test_project_detail_html_composition(client: Client, project):
    responses = assert_shell_composition(
        client,
        f"/projects/{project.pk}/",
        page_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "page-content"},
        tab_shell_kwargs={"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "tab-content"},
        page_container_id="page-content",
        tab_container_id="tab-content",
    )

    # Further custom assertions on individual responses
    assert responses["full_reload"].status_code == 200
```

> **Note:** `assert_shell_composition` requires `beautifulsoup4`. Install it via:
>
> ```bash
> pip install beautifulsoup4
> ```

## Related Resources

- **[Testing Utilities API Reference](api/testing.md):** Complete function signatures for `assert_shell_parity` and `assert_shell_composition`.
- **[Example Project Test Suite](https://github.com/lucas-rollin/django-htmx-nav/tree/main/example/htmx_nav_demo/tests):** Real-world parity and composition test implementations in the reference Helpdesk application.
