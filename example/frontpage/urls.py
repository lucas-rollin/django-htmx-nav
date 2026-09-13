from django.urls import path

from frontpage.views import guide, landing, robots_txt, sitemap_xml

urlpatterns = [
    path("", landing, name="landing"),
    path("guide/", guide, name="guide"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
]
