from django.urls import path

from . import views

app_name = "sandbox"

urlpatterns = [
    path("", views.item_list, name="item_list"),
]
