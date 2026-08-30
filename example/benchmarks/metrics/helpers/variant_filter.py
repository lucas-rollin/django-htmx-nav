"""
Shared --variants/--families resolution so every collect_*_metrics
command filters the registry identically.
"""


def resolve_variants(
    VARIANTS: dict, variants_opt: list[str] | None, families_opt: list[str] | None
) -> list:
    variants = list(VARIANTS.values())
    if variants_opt:
        variants = [v for v in variants if v.namespace in variants_opt]
    if families_opt:
        variants = [v for v in variants if v.family in families_opt]
    return variants
