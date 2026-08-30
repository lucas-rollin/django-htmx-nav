from django.urls import path

from . import views

app_name = "benchmarks"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("static/", views.metric_page, {"prefix": "static"}, name="static"),
    path("server/", views.metric_page, {"prefix": "server"}, name="server"),
    path("payload/", views.metric_page, {"prefix": "payload"}, name="payload"),
    path("client/", views.metric_page, {"prefix": "client"}, name="client"),
]
