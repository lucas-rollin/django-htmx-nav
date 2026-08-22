from .variants import Variant

VARIANTS = {
    "mpa": Variant(
        namespace="mpa",
        label="Vanilla MPA",
        group="mpa",
        views_module="mpa.views",
        url_prefix="mpa/",
        app_name="mpa",
    ),
    "htmx_nav_composite": Variant(
        namespace="htmx_nav_composite",
        label="Composite Swaps",
        group="package",
        views_module="htmx_nav_demo.views_composite",
        url_prefix="htmx-nav/composite/",
        app_name="htmx_nav_demo",
        uses_htmx=True,
        uses_htmx_nav=True,
    ),
    "htmx_nav_atomic": Variant(
        namespace="htmx_nav_atomic",
        label="Atomic Swaps",
        group="package",
        views_module="htmx_nav_demo.views_atomic",
        url_prefix="htmx-nav/atomic/",
        app_name="htmx_nav_demo",
        uses_htmx=True,
        uses_htmx_nav=True,
    ),
    "htmx_nav_declarative": Variant(
        namespace="htmx_nav_declarative",
        label="Declarative Context",
        group="package",
        views_module="htmx_nav_demo.views_declarative",
        url_prefix="htmx-nav/declarative/",
        app_name="htmx_nav_demo",
        uses_htmx=True,
        uses_htmx_nav=True,
    ),
}
