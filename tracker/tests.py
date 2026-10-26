from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .dashboard import build_emissions_chart
from .models import CarbonActivity
from .services import MEAT_FACTOR_IDS, estimate_meat


#Gunakan respons tiruan agar pengujian tidak memakai kuota Climatiq.
CHICKEN_RESULT = {"co2e": 0.420022996, "co2e_unit": "kg"}
BEEF_RESULT = {"co2e": 7.085123047, "co2e_unit": "kg"}


@override_settings(CLIMATIQ_API_KEY="test-key")
class MeatServiceTests(SimpleTestCase):
    @patch("tracker.services.requests.post")
    def test_each_meat_uses_its_factor_and_grams(self, post):
        for kind, result in (("chicken", CHICKEN_RESULT), ("beef", BEEF_RESULT)):
            with self.subTest(kind=kind):
                post.reset_mock()
                post.return_value.json.return_value = result
                response = estimate_meat(kind, Decimal("100"))

                post.return_value.raise_for_status.assert_called_once()
                self.assertEqual(post.call_args.kwargs["json"], {
                    "emission_factor": {"id": MEAT_FACTOR_IDS[kind]},
                    "parameters": {"weight": 100.0, "weight_unit": "g"},
                })
                self.assertEqual(response, result)

    @patch("tracker.services.requests.post")
    def test_unsupported_type_is_rejected_before_request(self, post):
        with self.assertRaises(ValueError):
            estimate_meat("unsupported", Decimal("100"))
        post.assert_not_called()


#Database pengujian terpisah menjaga catatan pengguna tetap utuh.
class MeatTrackerTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="meat-owner")
        self.other = get_user_model().objects.create_user(username="meat-other")
        self.index_url = reverse("tracker:index")

    #Kuantitas daging adalah perkiraan berat mentah dalam gram.
    def payload(self, **changes):
        data = {
            "activity_type": "chicken",
            "quantity": "100",
            "description": "Catatan daging",
            "date": timezone.localdate().isoformat(),
            "action": "estimate",
        }
        data.update(changes)
        return data

    def create_activity(self, **changes):
        data = {
            "user": self.owner, "activity_type": "chicken",
            "quantity": Decimal("100"), "emission_kg": Decimal("0.4200"),
            "date": timezone.localdate(),
        }
        data.update(changes)
        return CarbonActivity.objects.create(**data)

    @patch("tracker.activity_actions.estimate_meat", return_value=CHICKEN_RESULT)
    def test_preview_displays_grams_source_and_shortcuts_without_saving(self, estimate):
        response = self.client.post(self.index_url, self.payload())

        estimate.assert_called_once_with("chicken", Decimal("100"))
        self.assertEqual(response.context["estimate"], CHICKEN_RESULT)
        self.assertContains(response, 'id="quantity-unit" data-quantity-unit>g</span>')
        self.assertContains(response, "Prancis 2024")
        self.assertContains(response, 'data-meat-grams="150"')
        #Pastikan formulir hanya menyediakan empat aktivitas yang didukung.
        self.assertEqual(
            list(response.context["form"].fields["activity_type"].choices),
            [
                ("car_travel", "Mobil"),
                ("electricity", "Listrik"),
                ("chicken", "Ayam"),
                ("beef", "Daging sapi"),
            ],
        )
        self.assertEqual(CarbonActivity.objects.count(), 0)

    #Pratinjau AJAX mengembalikan JSON tanpa menyimpan atau menghitung ulang dashboard.
    @patch("tracker.views.build_dashboard_context")
    @patch("tracker.activity_actions.estimate_meat", return_value=CHICKEN_RESULT)
    def test_ajax_preview_returns_json_without_saving(self, estimate, dashboard):
        response = self.client.post(
            self.index_url, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"estimate": CHICKEN_RESULT, "errors": {}})
        self.assertEqual(CarbonActivity.objects.count(), 0)
        estimate.assert_called_once_with("chicken", Decimal("100"))
        dashboard.assert_not_called()

    @patch("tracker.activity_actions.estimate_meat")
    def test_ajax_preview_returns_field_errors_for_invalid_data(self, estimate):
        response = self.client.post(
            self.index_url, self.payload(quantity="-100"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.json()["estimate"])
        self.assertIn("quantity", response.json()["errors"])
        estimate.assert_not_called()

    @patch("tracker.activity_actions.estimate_meat", side_effect=requests.Timeout)
    def test_ajax_preview_api_failure_preserves_edited_activity(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]), self.payload(quantity="200"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["errors"])
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("100"))
        self.assertEqual(activity.emission_kg, Decimal("0.4200"))

    #AJAX tetap harus membawa token CSRF, sama seperti pengiriman formulir biasa.
    @patch("tracker.activity_actions.estimate_meat", return_value=CHICKEN_RESULT)
    def test_ajax_preview_requires_csrf_and_keeps_save_flow(self, estimate):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(
            self.index_url, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        ).status_code, 403)
        estimate.assert_not_called()
        client.get(self.index_url)
        data = self.payload(csrfmiddlewaretoken=client.cookies["csrftoken"].value)
        response = client.post(self.index_url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CarbonActivity.objects.count(), 0)
        client.force_login(self.owner)
        data["action"] = "save"
        response = client.post(self.index_url, data)
        self.assertRedirects(response, self.index_url)
        self.assertEqual(CarbonActivity.objects.count(), 1)

    #Penyimpanan AJAX memberi konfirmasi; GET berikutnya merender seluruh angka terbaru.
    @patch("tracker.activity_actions.estimate_meat", return_value=CHICKEN_RESULT)
    def test_ajax_save_returns_confirmation_and_fresh_dashboard(self, estimate):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.index_url + "?period=year", self.payload(action="save"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response.headers)
        activity = CarbonActivity.objects.get()
        self.assertEqual(activity.user, self.owner)
        self.assertEqual(response.json()["activity_id"], activity.pk)
        self.assertEqual(response.json()["message"], "Aktivitas berhasil disimpan.")
        self.assertEqual(response.json()["errors"], {})
        fresh = self.client.get(self.index_url, {"period": "year"})
        self.assertContains(fresh, 'id="tracker-dashboard"')
        self.assertContains(fresh, f'data-dashboard-url="{self.index_url}?period=year"')
        self.assertContains(
            fresh,
            f'href="{reverse("tracker:edit", args=[activity.pk])}?period=year#catat-cepat"',
        )
        self.assertEqual(fresh.context["period"], "year")
        self.assertEqual(fresh.context["total_emissions"], Decimal("0.4200"))
        self.assertEqual(fresh.context["activities"].count(), 1)
        self.assertFalse(fresh.context["form"].is_bound)

    @patch("tracker.activity_actions.estimate_meat", return_value={"co2e": 14.170246094})
    def test_ajax_edit_updates_same_record_and_returns_its_id(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]),
            self.payload(activity_type="beef", quantity="200", action="save"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["activity_id"], activity.pk)
        activity.refresh_from_db()
        self.assertEqual(activity.activity_type, "beef")
        self.assertEqual(activity.quantity, Decimal("200"))
        self.assertEqual(activity.emission_kg, Decimal("14.1702"))
        self.assertEqual(CarbonActivity.objects.count(), 1)

    @patch("tracker.activity_actions.estimate_meat")
    def test_ajax_save_rejects_anonymous_invalid_and_other_user_requests(self, estimate):
        activity = self.create_activity()
        response = self.client.post(
            self.index_url, self.payload(action="save"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["errors"])
        self.client.force_login(self.owner)
        response = self.client.post(
            self.index_url, self.payload(action="save", quantity="-100"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.json()["errors"])
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]), self.payload(action="save"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CarbonActivity.objects.count(), 1)
        estimate.assert_not_called()

    @patch("tracker.activity_actions.estimate_meat", side_effect=requests.Timeout)
    def test_ajax_save_api_error_keeps_existing_record(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]),
            self.payload(action="save", quantity="200"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["errors"])
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("100"))
        self.assertEqual(activity.emission_kg, Decimal("0.4200"))

    @patch("tracker.activity_actions.estimate_meat", side_effect=[CHICKEN_RESULT, BEEF_RESULT])
    def test_saved_meats_keep_separate_types_but_share_dashboard_category(self, estimate):
        self.client.force_login(self.owner)
        for kind in ("chicken", "beef"):
            response = self.client.post(
                self.index_url, self.payload(activity_type=kind, action="save"),
                follow=True,
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(CarbonActivity.objects.count(), 2)
        for kind, emission in (("chicken", "0.4200"), ("beef", "7.0851")):
            activity = CarbonActivity.objects.get(activity_type=kind)
            self.assertEqual(activity.user, self.owner)
            self.assertEqual(activity.quantity, Decimal("100"))
            self.assertEqual(activity.emission_kg, Decimal(emission))
        self.assertEqual(response.context["total_emissions"], Decimal("7.5051"))
        self.assertEqual(response.context["top_category"]["label"], "Daging")
        self.assertEqual(response.context["top_category"]["percentage"], Decimal("100"))
        self.assertContains(response, 'href="#i-utensils"')

    @patch("tracker.activity_actions.estimate_meat", return_value={"co2e": 14.170246094})
    def test_edit_can_change_meat_type_and_recalculate_same_record(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        url = reverse("tracker:edit", args=[activity.pk])
        response = self.client.get(url)
        self.assertEqual(response.context["form"].instance.pk, activity.pk)
        self.assertContains(response, 'id="quantity-unit" data-quantity-unit>g</span>')

        data = self.payload(activity_type="beef", quantity="200")
        self.client.post(url, data)
        activity.refresh_from_db()
        self.assertEqual(activity.activity_type, "chicken")
        self.assertEqual(activity.quantity, Decimal("100"))

        data["action"] = "save"
        self.client.post(url, data)
        activity.refresh_from_db()
        self.assertEqual(activity.activity_type, "beef")
        self.assertEqual(activity.quantity, Decimal("200"))
        self.assertEqual(activity.emission_kg, Decimal("14.1702"))
        self.assertEqual(activity.user, self.owner)
        self.assertEqual(CarbonActivity.objects.count(), 1)
        estimate.assert_called_with("beef", Decimal("200"))

    @patch("tracker.activity_actions.estimate_meat", side_effect=requests.Timeout)
    def test_api_failure_preserves_existing_record(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("tracker:edit", args=[activity.pk]),
            self.payload(quantity="200", action="save"),
        )
        self.assertContains(response, "Gagal menghitung emisi.")
        activity.refresh_from_db()
        self.assertEqual(activity.quantity, Decimal("100"))
        self.assertEqual(activity.emission_kg, Decimal("0.4200"))

    @patch("tracker.activity_actions.estimate_meat")
    def test_anonymous_user_cannot_save(self, estimate):
        response = self.client.post(self.index_url, self.payload(action="save"))
        self.assertContains(response, "Silakan login untuk menyimpan aktivitas.")
        estimate.assert_not_called()
        self.assertEqual(CarbonActivity.objects.count(), 0)

    @patch("tracker.activity_actions.estimate_meat")
    def test_other_user_cannot_edit_or_delete(self, estimate):
        activity = self.create_activity()
        self.client.force_login(self.other)
        for route in ("tracker:edit", "tracker:delete"):
            url = reverse(route, args=[activity.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.payload(action="save")).status_code, 404)
        self.assertTrue(CarbonActivity.objects.filter(pk=activity.pk).exists())
        estimate.assert_not_called()

    @patch("tracker.activity_actions.estimate_meat")
    def test_invalid_amounts_and_unsupported_types_are_rejected(self, estimate):
        for quantity in ("0", "-100"):
            response = self.client.post(self.index_url, self.payload(quantity=quantity))
            self.assertIn("quantity", response.context["form"].errors)
        #Tolak jenis aktivitas yang tidak dikenal dan pilihan kosong.
        for kind in ("unsupported", ""):
            response = self.client.post(self.index_url, self.payload(activity_type=kind))
            self.assertIn("activity_type", response.context["form"].errors)
        estimate.assert_not_called()
        self.assertEqual(CarbonActivity.objects.count(), 0)

    def test_delete_confirmation_preserves_grams_and_requires_csrf(self):
        activity = self.create_activity()
        self.create_activity(activity_type="beef", emission_kg=Decimal("7.0851"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse("tracker:delete", args=[activity.pk])
        response = client.get(url)
        self.assertContains(response, "Chicken meat (g)")
        self.assertTrue(CarbonActivity.objects.filter(pk=activity.pk).exists())
        self.assertEqual(client.post(url).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(url, {"csrfmiddlewaretoken": token}, follow=True)
        self.assertFalse(CarbonActivity.objects.filter(pk=activity.pk).exists())
        self.assertEqual(CarbonActivity.objects.count(), 1)
        self.assertEqual(response.context["total_emissions"], Decimal("7.0851"))

    #GET tidak menghapus; POST AJAX mengembalikan ID asli dan memperbarui ringkasan.
    def test_ajax_delete_returns_original_id_and_updates_dashboard(self):
        activity = self.create_activity()
        kept = self.create_activity(activity_type="beef", emission_kg=Decimal("7.0851"))
        self.client.force_login(self.owner)
        url = reverse("tracker:delete", args=[activity.pk])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, "data-delete-confirmation")
        self.assertEqual(CarbonActivity.objects.count(), 2)
        self.assertEqual(self.client.put(url).status_code, 405)
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "activity_id": activity.pk,
            "message": "Aktivitas berhasil dihapus.",
        })
        self.assertNotIn("Location", response.headers)
        self.assertFalse(CarbonActivity.objects.filter(pk=activity.pk).exists())
        self.assertTrue(CarbonActivity.objects.filter(pk=kept.pk).exists())
        fresh = self.client.get(self.index_url, {"period": "year"})
        self.assertEqual(fresh.context["total_emissions"], Decimal("7.0851"))
        self.assertEqual(fresh.context["period_emissions"], Decimal("7.0851"))
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 404)

    #Header AJAX tidak boleh melewati login, kepemilikan, atau perlindungan CSRF.
    def test_ajax_delete_requires_login_ownership_and_csrf(self):
        activity = self.create_activity()
        url = reverse("tracker:delete", args=[activity.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/profil/login/", response.url)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        client.get(url)
        self.assertEqual(client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertTrue(CarbonActivity.objects.filter(pk=activity.pk).exists())
        response = client.post(
            url, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CarbonActivity.objects.filter(pk=activity.pk).exists())

    def test_weekly_meat_category_excludes_other_users_and_dates(self):
        today = timezone.localdate()
        self.create_activity(emission_kg=Decimal("2"))
        self.create_activity(activity_type="beef", emission_kg=Decimal("6"))
        self.create_activity(activity_type="car_travel", emission_kg=Decimal("2"))
        self.create_activity(user=self.other, emission_kg=Decimal("999"))
        self.create_activity(date=today + timedelta(days=1), emission_kg=Decimal("100"))
        self.create_activity(
            date=today - timedelta(days=today.weekday() + 1),
            emission_kg=Decimal("100"),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.index_url)
        self.assertEqual(response.context["week_emissions"], Decimal("10"))
        self.assertEqual(response.context["top_category"]["emissions"], Decimal("8"))
        self.assertEqual(response.context["top_category"]["percentage"], Decimal("80"))

    #Periksa batas periode, isolasi pengguna, dan pilihan aktif pada template.
    @patch("tracker.views.timezone.localdate", return_value=date(2026, 10, 14))
    def test_period_filters_update_summary_categories_and_active_control(self, localdate):
        for day, amount, kind in (
            (date(2025, 12, 31), "999", "chicken"),
            (date(2026, 1, 1), "4", "car_travel"),
            (date(2026, 10, 1), "1", "chicken"),
            (date(2026, 10, 12), "2", "chicken"),
            (date(2026, 10, 14), "3", "beef"),
            (date(2026, 10, 15), "999", "chicken"),
        ):
            self.create_activity(date=day, emission_kg=Decimal(amount), activity_type=kind)
        self.create_activity(user=self.other, date=date(2026, 10, 14), emission_kg=Decimal("999"))
        self.client.force_login(self.owner)

        for requested, selected, label, total, meat_total in (
            ("week", "week", "Minggu ini", "5", "5"),
            ("month", "month", "Bulan ini", "6", "6"),
            ("year", "year", "Tahun ini", "10", "6"),
            ("invalid", "week", "Minggu ini", "5", "5"),
        ):
            with self.subTest(period=requested):
                response = self.client.get(self.index_url, {"period": requested})
                self.assertEqual(response.context["period"], selected)
                self.assertEqual(response.context["period_emissions"], Decimal(total))
                #Grafik dan ringkasan harus memakai rentang dan total yang sama.
                chart = response.context["daily_chart"]
                self.assertEqual(len(chart), {"week": 7, "month": 31, "year": 12}[selected])
                self.assertEqual(sum(bar["emissions"] for bar in chart), Decimal(total))
                self.assertContains(response, "Emisi bulanan" if selected == "year" else "Emisi harian")
                self.assertContains(response, f'--chart-columns: {len(chart)}')
                self.assertEqual(response.context["top_category"]["emissions"], Decimal(meat_total))
                self.assertEqual(response.context["today_emissions"], Decimal("3"))
                self.assertEqual(response.context["average_daily_emissions"], Decimal("5") / Decimal("7"))
                self.assertContains(response, f'href="?period={selected}" aria-current="true"')
                self.assertContains(response, f"Jejak karbonmu {label.lower()}.")
                self.assertEqual(response.content.count(b'aria-current="true"'), 1)

    @patch("tracker.activity_actions.estimate_car_travel", return_value={"co2e": 2.78283915682})
    @patch("tracker.activity_actions.estimate_electricity", return_value={"co2e": 6.8025})
    @patch("tracker.activity_actions.estimate_meat")
    def test_car_and_electricity_keep_their_own_calculators(self, meat, electricity, car):
        for activity_type, quantity in (("car_travel", "15"), ("electricity", "10")):
            response = self.client.post(
                self.index_url, self.payload(activity_type=activity_type, quantity=quantity)
            )
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["estimate"])
        car.assert_called_once_with(Decimal("15"))
        electricity.assert_called_once_with(Decimal("10"))
        meat.assert_not_called()


class DashboardChartTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="chart-owner")
        self.other = get_user_model().objects.create_user(username="chart-other")
        self.activities = CarbonActivity.objects.filter(user=self.owner)

    def log(self, day, emission, user=None):
        return CarbonActivity.objects.create(
            user=user or self.owner, activity_type="electricity",
            quantity=Decimal("1"), emission_kg=Decimal(emission), date=day,
        )

    #Data kosong tetap menyediakan seluruh label tanpa membagi dengan nol.
    def test_empty_periods_keep_zero_bars_and_future_markers(self):
        today = date(2026, 10, 14)
        for period, count in (("week", 7), ("month", 31), ("year", 12)):
            with self.subTest(period=period):
                chart = build_emissions_chart(self.activities, period, today)
                self.assertEqual(len(chart), count)
                self.assertTrue(all(bar["emissions"] == 0 and bar["height"] == 4 for bar in chart))
                self.assertFalse(chart[0]["is_future"])
                self.assertTrue(chart[-1]["is_future"])

    #Minggu yang melintasi pergantian tahun tetap dimulai pada Senin.
    def test_week_crosses_year_boundary_and_excludes_future_and_other_users(self):
        self.log(date(2025, 12, 28), "999")
        self.log(date(2025, 12, 29), "2")
        self.log(date(2026, 1, 1), "4")
        self.log(date(2026, 1, 2), "999")
        self.log(date(2026, 1, 1), "999", user=self.other)

        chart = build_emissions_chart(self.activities, "week", date(2026, 1, 1))
        self.assertEqual(chart[0]["date"], date(2025, 12, 29))
        self.assertEqual(chart[-1]["date"], date(2026, 1, 4))
        self.assertEqual([bar["label"] for bar in chart], ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"])
        self.assertEqual(sum(bar["emissions"] for bar in chart), Decimal("6"))
        self.assertEqual(chart[0]["height"], 95)
        self.assertEqual(chart[3]["height"], 190)
        self.assertFalse(chart[3]["is_future"])
        self.assertTrue(chart[4]["is_future"])
        self.assertEqual(chart[4]["emissions"], 0)

    #Jumlah hari Februari harus sesuai tahun kabisat dan tahun biasa.
    def test_month_respects_leap_year_and_calendar_boundaries(self):
        for year, last_day in ((2024, 29), (2026, 28)):
            with self.subTest(year=year):
                self.log(date(year, 1, 31), "999")
                self.log(date(year, 2, 1), "2")
                self.log(date(year, 2, last_day), "3")
                self.log(date(year, 3, 1), "999")
                chart = build_emissions_chart(self.activities, "month", date(year, 2, last_day))
                self.assertEqual(len(chart), last_day)
                self.assertEqual(chart[-1]["label"], str(last_day))
                self.assertEqual(sum(bar["emissions"] for bar in chart), Decimal("5"))
                self.assertFalse(any(bar["is_future"] for bar in chart))

    #Gabungkan catatan bulanan hanya dalam tahun ini sampai hari ini.
    def test_year_sums_months_and_excludes_future_records(self):
        for day, emission in (
            (date(2025, 12, 31), "999"),
            (date(2026, 1, 1), "3"),
            (date(2026, 1, 30), "2"),
            (date(2026, 10, 14), "1"),
            (date(2026, 10, 15), "999"),
            (date(2027, 1, 1), "999"),
        ):
            self.log(day, emission)
        chart = build_emissions_chart(self.activities, "year", date(2026, 10, 14))
        self.assertEqual(len(chart), 12)
        self.assertEqual(chart[0]["label"], "Jan")
        self.assertEqual(chart[-1]["label"], "Des")
        self.assertEqual(chart[0]["emissions"], Decimal("5"))
        self.assertEqual(chart[9]["emissions"], Decimal("1"))
        self.assertEqual(sum(bar["emissions"] for bar in chart), Decimal("6"))
        self.assertFalse(chart[9]["is_future"])
        self.assertTrue(chart[10]["is_future"])
