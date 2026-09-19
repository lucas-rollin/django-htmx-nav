from htmx_nav import Swap, has_messages, not_targeting, targeting

# Conditionals expressed in Python
swaps = [
    # Match exact target string
    Swap("nav/_tabs.html", include_if="tab-content"),

    # Match any of multiple DOM IDs
    Swap("nav/_breadcrumbs.html", include_if=targeting("main-content", "subtabs")),

    # Inverted targeting (skip sidebar if the sidebar itself was targeted)
    Swap("nav/_sidebar.html", include_if=not_targeting("sidebar")),

    # Built-in message predicate (skips if message queue is empty)
    Swap("nav/_messages.html", include_if=has_messages),

    # Custom callable / lambda checking permissions or request state
    Swap(
        "nav/_admin_badge.html",
        include_if=lambda req: req.user.is_staff,
    ),
]