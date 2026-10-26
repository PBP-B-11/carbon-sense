from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/edit/", views.index, name="edit"),
    path("<int:pk>/delete/", views.delete_activity, name="delete"),
]
