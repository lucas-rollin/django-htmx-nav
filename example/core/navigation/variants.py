"""
Variant configuration for the MPA / vanilla HTMX / django-htmx-nav comparison.

A "family" is one implementation approach (e.g. "vanilla HTMX,
composite OOB swaps"); its Python views and templates are fixed. 
Each family can additionally be explored along two independent, 
orthogonalUI-sync axes that only change HTML attributes, never Python:

    - hx_select: client-side fragment extraction instead of
      hx-target + server-built OOB swaps.
    - morph: idiomorph-based DOM morphing instead of a full
      innerHTML/outerHTML swap.

`make_family()` expands one implementation into a Variant per requested
axis combo, so registry.py declares each approach once instead of
copy-pasting near-identical Variant() calls per combo.
"""

from dataclasses import dataclass
from typing import Literal

Group = Literal["mpa", "vanilla", "package"]
NavigationComponent = Literal["sidebar", "breadcrumbs", "tabs", "subtabs", "steps"]

ALL_COMPONENTS: tuple[NavigationComponent, ...] = (
    "sidebar",
    "breadcrumbs",
    "tabs",
    "subtabs",
    "steps",
)

# Which nav regions a given content area's HX-Target implies keeping in sync.
# Shared data consumed by htmx_nav's own Swap wiring (Python) and by the
# vanilla hx-select/morph template tags.
TARGET_COMPONENTS: dict[str, list[NavigationComponent]] = {
    "main-content": ["sidebar", "breadcrumbs"],
    "tab-content": ["sidebar", "breadcrumbs", "tabs"],
    "subtab-content": ["sidebar", "breadcrumbs", "tabs", "subtabs"],
    "steps-content": ["sidebar", "breadcrumbs", "steps"],
}

# Group -> daisyUI color name, so the active approach's category is
# unambiguous at a glance in the navbar.
GROUP_COLORS: dict[Group, str] = {
    "mpa": "error",
    "vanilla": "warning",
    "package": "primary",
}

# (uses_hx_select, uses_morph) combinations a family can offer.
AxisCombo = tuple[bool, bool]
ALL_AXES: tuple[AxisCombo, ...] = (
    (False, False),
    (True, False),
    (False, True),
    (True, True),
)
MORPH_ONLY_AXES: tuple[AxisCombo, ...] = ((False, False), (False, True))
NO_AXES: tuple[AxisCombo, ...] = ((False, False),)


@dataclass(frozen=True)
class Variant:
    namespace: str
    label: str
    group: Group
    views_module: str
    url_prefix: str
    app_name: str = "core"

    component_swaps: list[NavigationComponent] | None = None
    uses_htmx: bool = True
    uses_htmx_nav: bool = False

    # Independent add-on axes. Both operate on whichever TARGET_COMPONENTS
    # a target_id implies, minus component_swaps.
    uses_hx_select: bool = False
    uses_morph: bool = False

    # Grouping metadata for the compact variant switcher: variants sharing
    # `family` are the same views/templates, differing only by axis flags.
    family: str = ""
    family_label: str = ""
    family_description: str = ""

    @property
    def color(self) -> str:
        return GROUP_COLORS[self.group]

    @property
    def axis_badge(self) -> str:
        """Compact label for this variant's enabled axes, used in the
        variant-switcher dropdown. Empty for the family's base variant."""
        bits = []
        if self.uses_hx_select:
            bits.append("hx-select")
        if self.uses_morph:
            bits.append("morph")
        return "+".join(bits)


def make_family(
    *,
    key: str,
    label: str,
    description: str,
    group: Group,
    views_module: str,
    url_prefix: str,
    app_name: str,
    component_swaps: list[NavigationComponent] | None = None,
    uses_htmx: bool = True,
    uses_htmx_nav: bool = False,
    axes: tuple[AxisCombo, ...] = ALL_AXES,
) -> dict[str, Variant]:
    """Expands one implementation into a Variant per axis combo in `axes`.

    `key`/`url_prefix` are used as-is for the (False, False) base
    variant; other combos get a `-hx-select`/`-morph` suffix appended
    to both, so every combo gets its own unique namespace and URL mount
    for free (config/urls.py just iterates VARIANTS.values()).
    """
    prefix = url_prefix.rstrip("/")
    variants: dict[str, Variant] = {}

    for hx_select, morph in axes:
        suffix = ("_hx_select" if hx_select else "") + ("_morph" if morph else "")
        namespace = f"{key}{suffix}"
        variants[namespace] = Variant(
            namespace=namespace,
            label=label,
            group=group,
            views_module=views_module,
            url_prefix=f"{prefix}{suffix.replace('_', '-')}/",
            app_name=app_name,
            component_swaps=component_swaps,
            uses_htmx=uses_htmx,
            uses_htmx_nav=uses_htmx_nav,
            uses_hx_select=hx_select,
            uses_morph=morph,
            family=key,
            family_label=label,
            family_description=description,
        )
    return variants