from dataclasses import dataclass
from typing import Literal

Group = Literal["mpa", "vanilla", "package"]
NavigationComponent = Literal["sidebar", "breadcrumbs", "tabs", "subtabs", "steps"]

# Which nav regions a given content area's HX-Target implies keeping in sync.
TARGET_COMPONENTS: dict[str, list[NavigationComponent]] = {
    "main-content": ["sidebar", "breadcrumbs"],
    "tab-content": ["sidebar", "breadcrumbs", "tabs"],
    "subtab-content": ["sidebar", "breadcrumbs", "tabs", "subtabs"],
    "steps-content": ["sidebar", "breadcrumbs", "steps"],
}


@dataclass(frozen=True)
class Variant:
    namespace: str
    label: str
    group: Group
    views_module: str
    url_prefix: str
    app_name: str = "core"

    uses_htmx: bool = False
    uses_htmx_nav: bool = False

    # Coverage set: components this variant ALREADY keeps in sync via its primary
    # mechanism (Python Swaps, target-aware partials, or hand-written OOB).
    component_swaps: list[NavigationComponent] | None = None

    # Two independent add-on axes, orthogonal to uses_htmx_nav and to each
    # other. Both operate on whatever TARGET_COMPONENTS - component_swaps
    # leaves uncovered for a given target_id, so they naturally no-op when
    # component_swaps already covers everything.
    uses_hx_select: bool = False
    uses_morph: bool = False