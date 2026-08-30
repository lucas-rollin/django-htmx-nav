"""
Per-family extra Python modules that participate in a variant's nav-sync
logic but live outside its views module, e.g. registry_declarative.py,
which htmx_nav_declarative's views_declarative.py imports from instead
of building Swaps inline.

Keyed by `variant.family` (not `variant.namespace`) since these files are
shared across a family's axis combos (htmx_nav_declarative_morph uses the
same registry_declarative.py as the base htmx_nav_declarative variant).

Add more entries here as the example project grows. collect() in
metrics/static_analysis.py takes an arbitrary list of dotted module
paths, so no code changes are needed elsewhere.
"""

EXTRA_MODULES_BY_FAMILY: dict[str, list[str]] = {
    "htmx_nav_declarative": ["htmx_nav_demo.registry_declarative"],
}


def extra_modules_for(family: str) -> list[str]:
    return EXTRA_MODULES_BY_FAMILY.get(family, [])
