from htmx_nav import Swap, render_nav, targeting


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    return render_nav(
        request,
        "projects/detail.html",
        {"project": project},
        # Which block is the main response? First match wins.
        partial={
            "#tab_content": targeting("tab-content"),
            "#content": True,  # fallback: any other HTMX request
        },
        # The tab bar lives inside #content, so it only needs to ride
        # along out-of-band when the response is just #tab_content.
        swaps=[
            Swap(
                "nav/_tabs.html", 
                target_id="tabs", 
                include_if=targeting("tab-content")
            ),
        ],
    )