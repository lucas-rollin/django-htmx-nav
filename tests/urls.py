from django.http import HttpResponse
from django.urls import path

from . import views


def dummy_view(request, **kwargs):
    return HttpResponse("ok")


urlpatterns = [
    path("workspace/", dummy_view, name="workspace"),
    path("detail/<int:pk>/", dummy_view, name="detail"),
    path("nav-workspace/", views.workspace_view, name="nav-workspace"),
    path("nav-detail/<int:pk>/", views.workspace_view, name="nav-detail"),
]
