from django.urls import include, path

from . import api_views, views

app_name = "challenges"

urlpatterns = [
    path("", views.daftar_tantangan, name="index"),
    path("json/", api_views.api_daftar_tantangan, name="json"),
    path("xml/", views.show_xml, name="show_xml"),
    path("xml/<uuid:id>/", views.show_xml_by_id, name="show_xml_by_id"),
    path("json/<uuid:id>/", views.show_json_by_id, name="show_json_by_id"),
    path("tambah/", views.tambah_tantangan, name="tambah"),
    path("<uuid:id>/ubah/", views.ubah_tantangan, name="ubah"),
    path("<uuid:id>/hapus/", views.hapus_tantangan, name="hapus"),
    path("api/", include("challenges.api_urls")),
]
