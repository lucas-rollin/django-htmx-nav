from .variants import TARGET_COMPONENTS


def oob_components(target_id: str, component_swaps: list[str] | None) -> list[str]:
    """Nav regions TARGET_COMPONENTS implies for target_id, minus whatever
    component_swaps already declares as covered."""
    components = TARGET_COMPONENTS.get(target_id, [])
    return [c for c in components if c not in (component_swaps or [])]
