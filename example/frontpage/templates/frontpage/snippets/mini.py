render_nav(
    request,
    "homepage.html",
    swaps=[
        Swap("_sidebar.html", target_id="sidebar"),
        Swap("_breadcrumbs.html", target_id="breadcrumbs"),
    ],
)