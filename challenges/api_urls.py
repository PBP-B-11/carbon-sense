from django.urls import path
from . import api_views

app_name = "challenges_api"

urlpatterns = [
    path("<uuid:id>/ikut/", api_views.api_ikuti, name="ikut"),
    path("<uuid:id>/checkin/", api_views.api_checkin, name="checkin"),
    path("<uuid:id>/berhenti/", api_views.api_berhenti, name="berhenti"),
    path("<uuid:id>/hapus/", api_views.api_hapus, name="hapus"),
]
