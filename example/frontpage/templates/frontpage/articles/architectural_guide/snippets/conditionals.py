from htmx_nav import Swap, targeting, not_targeting, has_messages 

# Conditionals expressed cleanly in Python: 
swaps = [ 
    # Match exact target string: 
    Swap("nav/_tabs.html", include_if="project-tabs"), 

    # Built-in targeting predicates matching one or multiple DOM IDs: 
    Swap("nav/_breadcrumbs.html", include_if=targeting("main-content", "subtabs")), 

    # Inverted targeting (e.g., skip sidebar if user targets the sidebar directly): 
    Swap("nav/_sidebar.html", include_if=not_targeting("sidebar")), 

    # Native message predicate: 
    Swap("nav/_messages.html", include_if=has_messages), 

    # Custom callable / lambda checking permissions or HTMX state: 
    Swap( 
        "nav/_admin_badge.html", 
        include_if=lambda req: req.user.is_staff and not req.htmx.boosted, 
    ), 
]