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

    uses_htmx: bool = False
    uses_htmx_nav: bool = False
    uses_idiomorph: bool = False

    hx_boost: bool = False
    hx_select: str | None = None
    hx_target: str | None = None
    hx_swap: str | None = None
