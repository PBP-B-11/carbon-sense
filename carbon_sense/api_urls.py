from django.urls import path

from challenges import api_views as challenges
from community import api_views as community
from home import api_views as home
from profil import api_views as profil
from tracker import api_views as tracker

app_name = "mobile_api"

urlpatterns = [
    path("home/", home.home, name="home"),
    path("auth/register/", profil.register, name="register"),
    path("auth/login/", profil.login, name="login"),
    path("auth/logout/", profil.logout, name="logout"),
    path("profile/", profil.profile, name="profile"),
    path("profile/cities/", profil.cities, name="cities"),
    path("profile/city/", profil.city, name="city"),
    path("profile/environment/", profil.environment, name="environment"),
    path("profile/password/", profil.password, name="password"),
    path("tracker/estimate/", tracker.estimate, name="estimate"),
    path("tracker/dashboard/", tracker.dashboard, name="dashboard"),
    path("tracker/activities/", tracker.activities, name="activities"),
    path("tracker/activities/<int:pk>/", tracker.activity_detail, name="activity"),
    path("challenges/", challenges.api_daftar_tantangan, name="challenges"),
    path("challenges/progress/", challenges.progress, name="challenge-progress"),
    path("challenges/badges/", challenges.badges, name="badges"),
    path("challenges/<uuid:id>/", challenges.api_detail_tantangan, name="challenge"),
    path("challenges/<uuid:id>/join/", challenges.api_ikuti, name="challenge-join"),
    path(
        "challenges/<uuid:id>/checkin/",
        challenges.api_checkin,
        name="challenge-checkin",
    ),
    path(
        "challenges/<uuid:id>/leave/", challenges.api_berhenti, name="challenge-leave"
    ),
    path("community/posts/", community.posts, name="posts"),
    path("community/posts/<uuid:pk>/", community.post_detail, name="post"),
    path("community/posts/<uuid:pk>/like/", community.like, name="like"),
    path("community/posts/<uuid:pk>/comments/", community.comments, name="comments"),
    path("community/comments/<int:pk>/", community.comment_detail, name="comment"),
    path("community/news/", community.news, name="news"),
    path("community/news/share/", community.share_news, name="share-news"),
]
