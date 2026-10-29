from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.index, name="index"),  # halaman feed modul 4
    path("post/new/", views.create_post, name="create_post"),  # buat post
    path("news/share/", views.share_news, name="share_news"),  # share news
    path(
        "post/<uuid:pk>/", views.post_detail, name="post_detail"
    ),  # cek komentar dari post
    path("post/<uuid:pk>/edit/", views.edit_post, name="edit_post"),  # edit post
    path("post/<uuid:pk>/delete/", views.delete_post, name="delete_post"),  # delete
    path("post/<uuid:pk>/like/", views.toggle_like, name="toggle_like"),  # like post
    path(
        "post/<uuid:pk>/comment/", views.add_comment, name="add_comment"
    ),  # tambahin komen
    path(
        "comment/<int:pk>/edit/", views.edit_comment, name="edit_comment"
    ),  # edit komen
    path(
        "comment/<int:pk>/delete/", views.delete_comment, name="delete_comment"
    ),  # delete komen
]
