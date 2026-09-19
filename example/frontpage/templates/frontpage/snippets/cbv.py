from django.views.generic import DetailView
from htmx_nav import Swap, make_shell_view_mixin

# Built from the same `render_shell` defined for function-based views
ShellViewMixin = make_shell_view_mixin(render_shell)


class ProjectBoardView(ShellViewMixin, DetailView):
    model = Project
    template_name = "pages/board.html"
    context_object_name = "project"

    def get_extra_swaps(self):
        # Sidebar & breadcrumbs come from the shell; view-specific extras go here
        return Swap("components/_status_badge.html", target_id="project-status")