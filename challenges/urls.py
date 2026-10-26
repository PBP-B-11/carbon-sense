from django.urls import include, path

from . import views

app_name = "challenges"

urlpatterns = [
    path("", views.daftar_tantangan, name="index"),
    path("tambah/", views.tambah_tantangan, name="tambah"),
    path("api/", include("challenges.api_urls")),
]
