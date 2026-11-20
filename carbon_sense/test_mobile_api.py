from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from challenges.models import Badge, Challenge
from community.news import CACHE_KEY
from profil.services import city_token
from tracker.models import CarbonActivity


class MobileAPITests(APITestCase):
    password = "Carbon-test-password-42"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user(username="mobile", password=self.password)
        self.web = Client()
        self.web.force_login(self.user)

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_account_uses_web_credentials_and_revokes_token(self):
        self.assertEqual(self.client.get("/api/v1/profile/").status_code, 401)
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": self.user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        self.assertEqual(
            self.client.get("/api/v1/profile/").json()["username"], "mobile"
        )
        response = self.client.put(
            "/api/v1/profile/",
            {"email": "mobile@example.org", "bio": "Mobile"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(self.web.get("/profil/"), "mobile@example.org")
        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/profile/").status_code, 401)

        self.auth(self.user)
        response = self.web.post(
            "/profil/password/",
            {
                "old_password": self.password,
                "new_password1": "Changed-web-password-42",
                "new_password2": "Changed-web-password-42",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/api/v1/profile/").status_code, 401)

    @patch("profil.views.search_cities")
    @patch("profil.api_views.environment_snapshot", return_value={"us_aqi": 42})
    def test_registration_city_password_and_delete(self, _snapshot, search):
        search.return_value = [{"name": "Depok", "latitude": -6.4, "longitude": 106.8}]
        token = self.client.get("/api/v1/profile/cities/?q=Depok").json()["results"][0][
            "token"
        ]
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "password1": self.password,
                "password2": self.password,
                "email": "new@example.org",
                "city": token,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        self.assertEqual(
            self.client.get("/api/v1/profile/").json()["city_name"], "Depok"
        )
        city = city_token({"name": "Bogor", "latitude": -6.6, "longitude": 106.8})
        self.assertEqual(
            self.client.put(
                "/api/v1/profile/city/", {"city": city}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/v1/profile/environment/").json(),
            {
                "city_name": "Bogor",
                "snapshot": {"us_aqi": 42},
            },
        )
        new_password = "Changed-mobile-password-42"
        response = self.client.post(
            "/api/v1/profile/password/",
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/profile/").status_code, 401)
        user = User.objects.get(username="newuser")
        self.assertTrue(user.check_password(new_password))
        self.auth(user)
        url = "/api/v1/profile/"
        self.assertEqual(
            self.client.delete(
                url, {"password": new_password, "confirm": "false"}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(
                url, {"password": new_password, "confirm": True}, format="json"
            ).status_code,
            204,
        )
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    @patch(
        "tracker.activity_actions.estimate_meat",
        return_value={"co2e": 1.23, "co2e_unit": "kg"},
    )
    def test_tracker_shares_activities_with_web_and_checks_ownership(self, _estimate):
        data = {
            "activity_type": "chicken",
            "quantity": "100",
            "date": str(timezone.localdate()),
        }
        response = self.client.post("/api/v1/tracker/estimate/", data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CarbonActivity.objects.exists())
        self.auth(self.user)
        url = "/api/v1/tracker/activities/"
        response = self.client.post(
            url, {**data, "description": "Dari Flutter"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        detail = f"{url}{response.json()['id']}/"
        self.assertEqual(response.json()["emission_kg"], "1.2300")
        self.assertContains(self.web.get("/tracker/"), "Dari Flutter")
        self.assertEqual(
            self.web.post("/tracker/", {**data, "action": "save"}).status_code, 302
        )
        self.assertEqual(self.client.get(url).json()["count"], 2)
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(self.client.put(detail, data, format="json").status_code, 200)
        self.assertEqual(
            self.client.get("/api/v1/tracker/dashboard/").json()["total_emissions"],
            2.46,
        )
        self.assertEqual(
            self.client.get("/api/v1/home/").json()["weekly_emissions"], 2.46
        )
        self.auth(User.objects.create_user(username="other"))
        self.assertEqual(self.client.get(url).json()["count"], 0)
        self.assertEqual(self.client.delete(detail).status_code, 404)
        self.auth(self.user)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_challenge_checkin_rewards_are_shared_with_web(self):
        badge = Badge.objects.create(
            name="Lencana", requirement="Selesaikan", icon="bike"
        )
        challenge = Challenge.objects.create(
            title="Naik sepeda",
            category="transportasi",
            duration_days=1,
            points=25,
            badge=badge,
        )
        url = f"/api/v1/challenges/{challenge.pk}/"
        self.assertEqual(self.client.get("/api/v1/challenges/").status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(f"{url}join/").status_code, 401)
        self.auth(self.user)
        self.assertEqual(self.client.post(f"{url}join/").status_code, 200)
        self.assertEqual(self.client.post(f"{url}leave/").status_code, 200)
        self.assertEqual(self.client.post(f"{url}checkin/").status_code, 400)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        browser.get("/challenges/")
        web_join = f"/api/tantangan/{challenge.pk}/ikut/"
        self.assertEqual(browser.post(web_join).status_code, 403)
        self.assertEqual(
            browser.post(
                web_join, HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value
            ).status_code,
            200,
        )
        progress = self.client.get("/api/v1/challenges/progress/").json()
        self.assertEqual(progress["active"]["challenge_id"], str(challenge.pk))
        self.assertTrue(self.client.post(f"{url}checkin/").json()["completed"])
        self.assertIsNotNone(
            self.client.get("/api/v1/challenges/badges/").json()[0]["earned_at"]
        )
        self.assertEqual(self.web.get("/challenges/").context["total_points"], 25)

    def test_community_crud_and_news(self):
        url = "/api/v1/community/posts/"
        self.assertEqual(self.client.get(url).json()["count"], 0)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 401)
        self.auth(self.user)
        response = self.client.post(
            url, {"category": "tips", "content": "Tips mobile"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        detail = f"{url}{response.json()['id']}/"
        self.assertContains(self.web.get("/community/"), "Tips mobile")
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(
            self.client.put(
                detail, {"category": "tips", "content": "Tips terbaru"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get(f"{url}?q=terbaru").json()["count"], 1)
        for _ in range(2):
            self.assertEqual(
                self.client.put(f"{detail}like/").json(), {"liked": True, "count": 1}
            )
        self.assertEqual(self.client.delete(f"{detail}like/").json()["count"], 0)
        comments = f"{detail}comments/"
        response = self.client.post(comments, {"content": "Komentar"}, format="json")
        self.assertEqual(response.status_code, 201)
        comment = f"/api/v1/community/comments/{response.json()['id']}/"
        self.assertEqual(self.client.get(comments).json()["count"], 1)
        self.assertEqual(
            self.client.put(comment, {"content": "Edit"}, format="json").status_code,
            200,
        )
        self.auth(User.objects.create_user(username="reader"))
        self.assertEqual(self.client.delete(comment).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 404)
        self.auth(self.user)
        self.assertEqual(self.client.delete(comment).status_code, 204)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        article = {
            "url": "https://example.org/news",
            "title": "Berita",
            "source": "Sumber",
            "snippet": "",
        }
        cache.set(CACHE_KEY, [article])
        self.assertEqual(
            self.client.get("/api/v1/community/news/").json()["results"], [article]
        )
        response = self.client.post(
            "/api/v1/community/news/share/", {"url": article["url"]}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["category"], "berita")
