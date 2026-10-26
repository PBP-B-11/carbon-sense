from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import UserProfile
from .services import _get, city_token, environment_snapshot


@override_settings(
    MIDDLEWARE=[
        middleware
        for middleware in settings.MIDDLEWARE
        if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
    ]
)
class ProfileTests(TestCase):
    def setUp(self):
        self.city = city_token({"name": "Depok", "latitude": -6.4, "longitude": 106.8})
        self.user = User.objects.create_user(
            "faishal", "old@example.com", "Strong-pass123"
        )
        self.profile = UserProfile.objects.create(
            user=self.user, city_name="Jakarta", latitude=-6.2, longitude=106.8
        )

    @patch("profil.views.environment_snapshot", return_value=None)
    def test_profile_requires_login(self, _snapshot):
        response = self.client.get(reverse("profil:index"))
        self.assertRedirects(
            response, f"{reverse('profil:login')}?next={reverse('profil:index')}"
        )

    def test_login_keeps_requested_destination(self):
        response = self.client.get(
            f"{reverse('profil:login')}?next={reverse('profil:index')}"
        )
        self.assertContains(response, f'name="next" value="{reverse("profil:index")}"')

    @patch(
        "profil.views.environment_snapshot",
        return_value={
            "temperature_2m": 28.0,
            "relative_humidity_2m": 75,
            "wind_speed_10m": 8.5,
            "us_aqi": 52,
        },
    )
    def test_profile_renders_environment_snapshot(self, _snapshot):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profil:index"))
        self.assertContains(response, "US AQI estimate: 52")

    @patch("profil.services._get")
    def test_weather_stays_visible_when_air_api_fails(self, get):
        get.side_effect = [
            {
                "current": {
                    "temperature_2m": 29.2,
                    "relative_humidity_2m": 66,
                    "wind_speed_10m": 7.4,
                }
            },
            None,
        ]
        self.client.force_login(self.user)
        response = self.client.get(reverse("profil:index"))
        self.assertEqual(response.context["snapshot"]["temperature_2m"], 29.2)
        self.assertContains(response, "Suhu")
        self.assertNotContains(response, "US AQI estimate:")

    @patch("profil.services.requests.get")
    def test_api_retries_refused_connection(self, get):
        get.side_effect = [
            requests.ConnectionError("refused"),
            Mock(json=lambda: {"current": {"temperature_2m": 29.2}}),
        ]
        self.assertEqual(
            _get("https://api.open-meteo.com"), {"current": {"temperature_2m": 29.2}}
        )
        self.assertEqual(get.call_count, 2)

    @patch("profil.services._get")
    def test_aqi_remains_available_on_next_snapshot(self, get):
        cache.clear()
        self.addCleanup(cache.clear)
        weather = {"current": {"temperature_2m": 29.2}}
        air = {"current": {"us_aqi": 174}}
        get.side_effect = [weather, air, weather]
        self.assertEqual(environment_snapshot(self.profile)["us_aqi"], 174)
        self.assertEqual(environment_snapshot(self.profile)["us_aqi"], 174)

    def test_registration_creates_profile_with_city(self):
        response = self.client.post(
            reverse("profil:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Strong-pass123",
                "password2": "Strong-pass123",
                "city": self.city,
            },
        )
        user = User.objects.get(username="newuser")
        self.assertRedirects(response, reverse("profil:index"))
        self.assertEqual(user.userprofile.city_name, "Depok")
        self.assertEqual(user.userprofile.latitude, -6.4)

    def test_registration_explains_invalid_city_and_keeps_search(self):
        response = self.client.post(
            reverse("profil:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Strong-pass123",
                "password2": "Strong-pass123",
                "city": "",
                "city_search": "Depok",
            },
        )
        self.assertContains(response, "Periksa isian berikut:")
        self.assertContains(response, "Pilih kota dari hasil pencarian.")
        self.assertContains(response, 'value="Depok"')
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_profile_and_city_updates(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("profil:update"),
            {"email": "new@example.com", "bio": "Menanam pohon."},
        )
        self.client.post(reverse("profil:city"), {"city": self.city})
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.profile.bio, "Menanam pohon.")
        self.assertEqual(self.profile.city_name, "Depok")

    @patch("profil.views.environment_snapshot", return_value=None)
    def test_ajax_city_save_returns_new_widget_and_rejects_invalid_city(self, snapshot):
        self.client.force_login(self.user)
        url = reverse("profil:city")
        headers = {"HTTP_ACCEPT": "application/json"}

        invalid = self.client.post(url, {"city": "invalid"}, **headers)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("error", invalid.json())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.city_name, "Jakarta")

        response = self.client.post(url, {"city": self.city}, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["city"], "Depok")
        self.assertIn("Cuaca dan udara di Depok", response.json()["air_html"])
        self.assertIn(
            "Data lingkungan saat ini tidak tersedia.", response.json()["air_html"]
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.city_name, "Depok")
        snapshot.assert_called_once_with(self.profile)

    @patch("profil.views.environment_snapshot", return_value=None)
    def test_invalid_updates_show_errors(self, _snapshot):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profil:update"), {"email": "invalid", "bio": ""}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["email_form"].errors)

        response = self.client.post(reverse("profil:city"), {"city": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["city_form"].errors)

    def test_delete_needs_valid_password_and_confirmation(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("profil:delete"), {"password": "wrong", "confirm": "on"}
        )
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        response = self.client.post(
            reverse("profil:delete"), {"password": "Strong-pass123", "confirm": "on"}
        )
        self.assertRedirects(response, reverse("home:index"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(pk=self.profile.pk).exists())
