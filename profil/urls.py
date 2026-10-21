from django.urls import path

from . import views

app_name = "profil"

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("cities/", views.city_search, name="cities"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.sign_out, name="logout"),
    path("update/", views.update_profile, name="update"),
    path("city/", views.update_city, name="city"),
    path("password/", views.ChangePasswordView.as_view(), name="password"),
    path("delete/", views.delete_account, name="delete"),
]
