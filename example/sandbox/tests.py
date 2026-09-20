from django.test import Client
from django.urls import reverse

from htmx_nav.testing import assert_shell_parity


def test_item_list_navigation_parity(client: Client):
    assert_shell_parity(
        client,
        reverse("sandbox:item_list"),
        requests={
            "full_reload": {},
            "page_shell": {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "main-content"},
        },
        checks={
            "breadcrumbs": lambda ctx: [c["label"] for c in ctx["breadcrumbs"]],
        },
    )
