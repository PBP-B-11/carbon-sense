from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from challenges.models import Challenge
from tracker.models import CarbonActivity

User = get_user_model()


class HomePageTests(TestCase):
    """Pengujian integrasi data dinamis pada halaman utama (Beranda)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="user_home", password="password123"
        )
        self.challenge = Challenge.objects.create(
            title="Tantangan Hijau Mingguan",
            description="Hemat listrik dan jalan kaki.",
            category=Challenge.Category.ENERGY,
            duration_days=7,
            points=40,
            estimated_saving_kg="3.5",
        )

    def test_home_page_unauthenticated(self):
        """Memverifikasi bahwa halaman beranda dapat diakses publik dengan konten dinamis."""
        res = self.client.get(reverse("home:index"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Kenali Jejakmu")
        self.assertContains(res, "Tantangan Hijau Mingguan")
        self.assertContains(res, "Berita hangat")
        self.assertNotContains(res, "[JUDUL BERITA DARI GNEWS]")

    def test_home_page_authenticated_weekly_emissions(self):
        """Memverifikasi bahwa total emisi minggu ini dihitung dinamis dari aktivitas pengguna."""
        self.client.force_login(self.user)
        CarbonActivity.objects.create(
            user=self.user,
            activity_type="car_travel",
            description="Perjalanan kantor",
            quantity=Decimal("15.0"),
            emission_kg=Decimal("2.85"),
            date=timezone.localdate(),
        )

        res = self.client.get(reverse("home:index"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["weekly_emissions"], Decimal("2.85"))
        self.assertContains(res, "2,9")


class StaticFilesTests(SimpleTestCase):
    def test_css_is_served_without_collectstatic(self):
        with TemporaryDirectory() as static_root:
            with override_settings(DEBUG=False, STATIC_ROOT=static_root):
                response = self.client.get(
                    "/static/css/styles.css",
                    HTTP_HOST="faishal-falih-carbon-sense.pws.cs.ui.ac.id",
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/css"))
