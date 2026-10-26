from decimal import Decimal
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import CarbonActivity
from .services import LPG_FACTOR_ID, estimate_lpg


#Gunakan hasil API tiruan agar pengujian tidak memakai kuota Climatiq.
LPG_RESULT = {"co2e": 0.293936095, "co2e_unit": "kg"}


@override_settings(CLIMATIQ_API_KEY="test-key")
class LPGServiceTests(SimpleTestCase):
    @patch("tracker.services.requests.post")
    def test_request_uses_kilograms_instead_of_meal_count(self, post):
        post.return_value.json.return_value = LPG_RESULT

        result = estimate_lpg(Decimal("0.10"))

        post.return_value.raise_for_status.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"], {
            "emission_factor": {"id": LPG_FACTOR_ID},
            "parameters": {"weight": 0.1, "weight_unit": "kg"},
        })
        self.assertEqual(result, LPG_RESULT)


#TestCase menggunakan database pengujian yang terpisah dari data pengguna.
class LPGTrackerTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="lpg-owner")
        self.other = get_user_model().objects.create_user(username="lpg-other")
        self.index_url = reverse("tracker:index")

    #Kuantitas formulir adalah berat gas yang dikonsumsi dalam kg.
    def payload(self, **changes):
        data = {
            "activity_type": "lpg",
            "quantity": "0.10",
            "description": "Gas untuk memasak",
            "date": timezone.localdate().isoformat(),
            "action": "estimate",
        }
        data.update(changes)
        return data

    def create_activity(self, **changes):
        data = {
            "user": self.owner, "activity_type": "lpg",
            "quantity": Decimal("0.10"), "emission_kg": Decimal("0.2939"),
            "date": timezone.localdate(),
        }
        data.update(changes)
        return CarbonActivity.objects.create(**data)

    @patch("tracker.views.estimate_lpg", return_value=LPG_RESULT)
    def test_preview_displays_units_and_source_without_saving(self, estimate):
        response = self.client.post(self.index_url, self.payload())

        estimate.assert_called_once_with(Decimal("0.10"))
        self.assertEqual(response.context["estimate"], LPG_RESULT)
        self.assertContains(response, 'id="quantity-unit">kg</span>')
        self.assertContains(response, "UK Government 2025 (Inggris)")
        self.assertNotContains(response, 'value="meal"')
        self.assertEqual(CarbonActivity.objects.count(), 0)

    @patch("tracker.views.estimate_lpg", return_value=LPG_RESULT)
    def test_save_assigns_owner_and_updates_history_and_categories(self, estimate):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.index_url, self.payload(action="save"), follow=True
        )

        activity = CarbonActivity.objects.get()
        self.assertEqual(activity.user, self.owner)
        self.assertEqual(activity.activity_type, "lpg")
        self.assertEqual(activity.quantity, Decimal("0.10"))
        self.assertEqual(activity.emission_kg, Decimal("0.2939"))
        self.assertEqual(response.context["total_emissions"], Decimal("0.2939"))
        self.assertEqual(response.context["top_category"]["label"], "Gas LPG")
        self.assertEqual(response.context["top_category"]["percentage"], Decimal("100"))
        self.assertContains(response, "Gas untuk memasak")
        self.assertContains(response, 'href="#i-flame"')

    @patch("tracker.views.estimate_lpg", return_value={"co2e": 0.58787219})
    def test_edit_recalculates_same_record_and_preview_does_not_save(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        url = reverse("tracker:edit", args=[activity.pk])
        response = self.client.get(url)
        self.assertEqual(response.context["form"].instance.pk, activity.pk)
        self.assertContains(response, 'id="quantity-unit">kg</span>')

        self.client.post(url, self.payload(quantity="0.20"))
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("0.10"))

        self.client.post(url, self.payload(quantity="0.20", action="save"))
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("0.20"))
        self.assertEqual(activity.emission_kg, Decimal("0.5879"))
        self.assertEqual(activity.user, self.owner)
        self.assertEqual(CarbonActivity.objects.count(), 1)

    @patch("tracker.views.estimate_lpg", side_effect=requests.Timeout)
    def test_api_failure_preserves_existing_activity(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]),
            self.payload(quantity="0.20", action="save"),
        )

        self.assertContains(response, "Gagal menghitung emisi.")
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("0.10"))
        self.assertEqual(activity.emission_kg, Decimal("0.2939"))

    @patch("tracker.views.estimate_lpg")
    def test_anonymous_user_cannot_save(self, estimate):
        response = self.client.post(self.index_url, self.payload(action="save"))

        self.assertContains(response, "Silakan login untuk menyimpan aktivitas.")
        estimate.assert_not_called()
        self.assertEqual(CarbonActivity.objects.count(), 0)

    @patch("tracker.views.estimate_lpg")
    def test_other_user_cannot_edit_or_delete(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.other)

        for route in ("tracker:edit", "tracker:delete"):
            url = reverse(route, args=[activity.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.payload(action="save")).status_code, 404)

        self.assertTrue(CarbonActivity.objects.filter(pk=activity.pk).exists())
        estimate.assert_not_called()

    @patch("tracker.views.estimate_lpg")
    def test_invalid_quantities_and_retired_food_choice_are_rejected(self, estimate):
        for quantity in ("0", "-0.10"):
            with self.subTest(quantity=quantity):
                response = self.client.post(self.index_url, self.payload(quantity=quantity))
                self.assertIn("quantity", response.context["form"].errors)

        response = self.client.post(self.index_url, self.payload(activity_type="meal"))
        self.assertIn("activity_type", response.context["form"].errors)
        estimate.assert_not_called()
        self.assertEqual(CarbonActivity.objects.count(), 0)

    def test_confirmed_delete_requires_csrf_and_updates_total(self):
        activity = self.create_activity()
        self.create_activity(quantity=Decimal("0.20"), emission_kg=Decimal("0.5879"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse("tracker:delete", args=[activity.pk])

        response = client.get(url)
        self.assertContains(response, "Cooking gas LPG (kg)")
        self.assertTrue(CarbonActivity.objects.filter(pk=activity.pk).exists())
        self.assertEqual(client.post(url).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(url, {"csrfmiddlewaretoken": token}, follow=True)

        self.assertFalse(CarbonActivity.objects.filter(pk=activity.pk).exists())
        self.assertEqual(CarbonActivity.objects.count(), 1)
        self.assertEqual(response.context["total_emissions"], Decimal("0.5879"))

    @patch("tracker.views.estimate_car_travel", return_value={"co2e": 2.78283915682})
    @patch("tracker.views.estimate_electricity", return_value={"co2e": 6.8025})
    @patch("tracker.views.estimate_lpg")
    def test_car_and_electricity_keep_their_own_calculators(self, lpg, electricity, car):
        for activity_type, quantity in (("car_travel", "15"), ("electricity", "10")):
            response = self.client.post(
                self.index_url, self.payload(activity_type=activity_type, quantity=quantity)
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["estimate"])

        car.assert_called_once_with(Decimal("15"))
        electricity.assert_called_once_with(Decimal("10"))
        lpg.assert_not_called()
