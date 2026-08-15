"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from importlib import import_module

from core.navigation.registry import VARIANTS
from core.urls import generate_variant_urls
from django.urls import include, path
from django.views.generic import RedirectView


def _variant_mounts():
    for variant in VARIANTS.values():
        views = import_module(variant.views_module)
        yield path(
            variant.url_prefix,
            include(
                (generate_variant_urls(views), variant.app_name),
                namespace=variant.namespace,
            ),
        )


urlpatterns = [
    path("", RedirectView.as_view(url="/mpa/", permanent=True)),
    *_variant_mounts(),
]
