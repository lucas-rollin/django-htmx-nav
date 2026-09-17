from django.urls import path

from frontpage.views import demo_entry, guide, landing, robots_txt, sitemap_xml

urlpatterns = [
    path("", landing, name="landing"),
    path("guide/", guide, name="guide"),
    path("demo/", demo_entry, name="demo_entry"),
    path("demo/<str:variant>/", demo_entry, name="demo_entry"),
    path("demo/<str:variant>/<str:url_name>/", demo_entry, name="demo_entry"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
]
