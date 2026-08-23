from dataclasses import dataclass
from typing import Literal

Group = Literal[
    "mpa",
    "vanilla",
    "package",
]


@dataclass(frozen=True)
class Variant:
    namespace: str
    label: str
    group: Group
    views_module: str
    url_prefix: str
    app_name: str = "core"

    component_swaps: list[str] = False # ids of navigation component swaps
    uses_htmx: bool = False
    uses_htmx_nav: bool = False
    uses_idiomorph: bool = False
