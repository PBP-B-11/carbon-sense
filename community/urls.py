from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.index, name="index"),
    path("post/new/", views.create_post, name="create_post"),
    path("post/<uuid:pk>/", views.post_detail, name="post_detail"),
    path("post/<uuid:pk>/edit/", views.edit_post, name="edit_post"),
    path("post/<uuid:pk>/delete/", views.delete_post, name="delete_post"),
    path("post/<uuid:pk>/like/", views.toggle_like, name="toggle_like"),
    path("post/<uuid:pk>/comment/", views.add_comment, name="add_comment"),
]
