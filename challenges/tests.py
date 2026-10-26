from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from challenges.models import (
    Badge,
    Challenge,
    CheckIn,
    Participation,
    PointEntry,
    UserBadge,
)
from challenges.utils import (
    hitung_streak,
    periksa_lencana_streak,
    ringkasan_pengguna,
    sudah_checkin_hari_ini,
    total_poin,
)

User = get_user_model()


class ChallengeModelTests(TestCase):
    """Pengujian representasi string dan batasan constraint model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user_model", email="model@example.com", password="password123"
        )
        self.badge = Badge.objects.create(
            name="Pesepeda",
            requirement="Selesaikan tantangan Sepeda ke kampus.",
            icon="bike",
            tone="amber",
        )
        self.challenge = Challenge.objects.create(
            title="Sepeda ke kampus",
            description="Ganti tiga perjalanan motor dengan sepeda.",
            category=Challenge.Category.TRANSPORT,
            duration_days=7,
            points=50,
            estimated_saving_kg="2.4",
            badge=self.badge,
            icon="bike",
            tone="amber",
        )

    def test_model_str_representations(self):
        """Memverifikasi fungsi __str__ seluruh model challenges."""
        self.assertEqual(str(self.badge), "Pesepeda")
        self.assertEqual(str(self.challenge), "Sepeda ke kampus")

        partisipasi = Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        self.assertIn("active", str(partisipasi))

        checkin = CheckIn.objects.create(
            participation=partisipasi, date=timezone.localdate()
        )
        self.assertIn(str(timezone.localdate()), str(checkin))

        user_badge = UserBadge.objects.create(user=self.user, badge=self.badge)
        self.assertIn("Pesepeda", str(user_badge))

        point = PointEntry.objects.create(user=self.user, delta=50, reason="Uji poin")
        self.assertIn("+50", str(point))

    def test_unique_active_participation_constraint(self):
        """Memverifikasi bahwa pengguna tidak dapat memiliki dua partisipasi aktif untuk tantangan yang sama."""
        Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        with self.assertRaises(IntegrityError):
            Participation.objects.create(
                user=self.user,
                challenge=self.challenge,
                started_at=timezone.localdate(),
            )

    def test_unique_check_in_per_day_constraint(self):
        """Memverifikasi bahwa pengguna tidak dapat check-in dua kali pada tanggal yang sama di database."""
        partisipasi = Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        CheckIn.objects.create(participation=partisipasi, date=timezone.localdate())
        with self.assertRaises(IntegrityError):
            CheckIn.objects.create(participation=partisipasi, date=timezone.localdate())


class ChallengeUtilsTests(TestCase):
    """Pengujian fungsi utilitas perhitungan poin, streak, dan evaluasi lencana."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user_utils", email="utils@example.com", password="password123"
        )
        self.badge_7 = Badge.objects.create(
            name="Hijau 7 hari",
            requirement="Check-in tujuh hari berturut-turut.",
            icon="leaf",
            tone="moss",
        )
        self.badge_30 = Badge.objects.create(
            name="Pejuang 30 hari",
            requirement="Check-in tiga puluh hari berturut-turut.",
            icon="award",
            tone="amber",
        )
        self.challenge = Challenge.objects.create(
            title="Tantangan Uji",
            description="Deskripsi",
            category=Challenge.Category.ENERGY,
            duration_days=30,
            points=100,
            estimated_saving_kg="10.0",
        )
        self.partisipasi = Participation.objects.create(
            user=self.user,
            challenge=self.challenge,
            started_at=timezone.localdate() - timedelta(days=35),
        )

    def test_total_poin_and_ringkasan(self):
        """Memverifikasi agregasi total poin dan ringkasan profil tantangan."""
        self.assertEqual(total_poin(self.user), 0)
        PointEntry.objects.create(user=self.user, delta=50, reason="Tantangan 1")
        PointEntry.objects.create(user=self.user, delta=30, reason="Tantangan 2")
        self.assertEqual(total_poin(self.user), 80)

        ringkasan = ringkasan_pengguna(self.user)
        self.assertEqual(ringkasan["poin"], 80)
        self.assertEqual(ringkasan["diikuti"], 1)
        self.assertEqual(ringkasan["selesai"], 0)
        self.assertEqual(ringkasan["lencana"], 0)

    def test_sudah_checkin_hari_ini(self):
        """Memverifikasi fungsi pengecekan check-in hari ini."""
        self.assertFalse(sudah_checkin_hari_ini(self.user))
        CheckIn.objects.create(
            participation=self.partisipasi, date=timezone.localdate()
        )
        self.assertTrue(sudah_checkin_hari_ini(self.user))

    def test_hitung_streak_berturut_turut_dan_lencana(self):
        """Memverifikasi bahwa streak bertambah dengan check-in berturut-turut dan memicu lencana streak."""
        hari_ini = timezone.localdate()
        for i in range(7):
            CheckIn.objects.create(
                participation=self.partisipasi, date=hari_ini - timedelta(days=6 - i)
            )

        self.assertEqual(hitung_streak(self.user), 7)
        lencana_diberikan = periksa_lencana_streak(self.user)
        self.assertIn("Hijau 7 hari", lencana_diberikan)
        self.assertTrue(
            UserBadge.objects.filter(user=self.user, badge=self.badge_7).exists()
        )

    def test_hitung_streak_masih_berjalan_sebelum_tengah_malam(self):
        """Memverifikasi bahwa streak tidak langsung reset jika hari ini belum check-in tapi kemarin check-in."""
        kemarin = timezone.localdate() - timedelta(days=1)
        CheckIn.objects.create(participation=self.partisipasi, date=kemarin)
        self.assertEqual(hitung_streak(self.user), 1)

    def test_hitung_streak_reset_jika_bolong(self):
        """Memverifikasi bahwa streak bernilai nol jika ada hari yang terlewat."""
        dua_hari_lalu = timezone.localdate() - timedelta(days=2)
        CheckIn.objects.create(participation=self.partisipasi, date=dua_hari_lalu)
        self.assertEqual(hitung_streak(self.user), 0)


class ChallengeViewsTests(TestCase):
    """Pengujian view berbasis template dan proteksi role superuser."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="user_biasa", email="biasa@example.com", password="password123"
        )
        self.admin = User.objects.create_superuser(
            username="user_admin", email="admin@example.com", password="password123"
        )
        self.challenge1 = Challenge.objects.create(
            title="Tantangan Transportasi",
            description="Deskripsi",
            category=Challenge.Category.TRANSPORT,
            duration_days=5,
            points=40,
        )
        self.challenge2 = Challenge.objects.create(
            title="Tantangan Energi",
            description="Deskripsi",
            category=Challenge.Category.ENERGY,
            duration_days=5,
            points=30,
        )

    def test_daftar_tantangan_login_required(self):
        """Memverifikasi redirect ke halaman login untuk user yang belum terautentikasi."""
        response = self.client.get(reverse("challenges:index"))
        self.assertEqual(response.status_code, 302)

    def test_daftar_tantangan_get_authenticated(self):
        """Memverifikasi halaman daftar tantangan berhasil dirender untuk user terautentikasi."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("challenges:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tantangan Transportasi")
        self.assertContains(response, "Tantangan Energi")

    def test_daftar_tantangan_filter_kategori(self):
        """Memverifikasi filter kategori tantangan pada URL query."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("challenges:index") + "?kategori=transportasi"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tantangan Transportasi")
        self.assertNotContains(response, "Tantangan Energi")

    def test_form_post_ikut_membatasi_satu_tantangan_aktif(self):
        """Memverifikasi penolakan form POST ikut tantangan jika pengguna sudah punya tantangan aktif."""
        self.client.force_login(self.user)
        # Ikuti tantangan pertama
        self.client.post(
            reverse("challenges:index"),
            {"aksi": "ikut", "tantangan_id": str(self.challenge1.id)},
        )
        self.assertTrue(
            Participation.objects.filter(
                user=self.user, challenge=self.challenge1, status="active"
            ).exists()
        )

        # Mencoba mengikuti tantangan kedua saat yang pertama masih aktif
        response = self.client.post(
            reverse("challenges:index"),
            {"aksi": "ikut", "tantangan_id": str(self.challenge2.id)},
            follow=True,
        )
        self.assertContains(response, "Kamu masih memiliki tantangan aktif")
        self.assertFalse(
            Participation.objects.filter(
                user=self.user, challenge=self.challenge2, status="active"
            ).exists()
        )

    def test_tambah_tantangan_forbidden_untuk_user_biasa(self):
        """Memverifikasi bahwa pengguna biasa mendapat response 403 Forbidden pada halaman tambah tantangan."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("challenges:tambah"))
        self.assertEqual(response.status_code, 403)

    def test_tambah_tantangan_bisa_diakses_superuser(self):
        """Memverifikasi bahwa superuser dapat mengakses dan menambahkan tantangan baru."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("challenges:tambah"))
        self.assertEqual(response.status_code, 200)

        post_data = {
            "title": "Tantangan Baru Admin",
            "description": "Deskripsi baru",
            "category": "transportasi",
            "duration_days": 7,
            "points": 50,
            "estimated_saving_kg": "3.5",
            "icon": "bike",
            "tone": "amber",
        }
        res_post = self.client.post(reverse("challenges:tambah"), post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertTrue(Challenge.objects.filter(title="Tantangan Baru Admin").exists())

    def test_hapus_tantangan_forbidden_untuk_user_biasa(self):
        """Memverifikasi bahwa pengguna biasa mendapat response 403 Forbidden saat mencoba menghapus tantangan."""
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("challenges:hapus", kwargs={"id": self.challenge1.id})
        )
        self.assertEqual(response.status_code, 403)

        post_res = self.client.post(
            reverse("challenges:hapus", kwargs={"id": self.challenge1.id})
        )
        self.assertEqual(post_res.status_code, 403)
        self.assertTrue(Challenge.objects.filter(id=self.challenge1.id).exists())

    def test_hapus_tantangan_bisa_diakses_superuser(self):
        """Memverifikasi bahwa superuser dapat melihat konfirmasi dan menghapus tantangan."""
        self.client.force_login(self.admin)
        get_res = self.client.get(
            reverse("challenges:hapus", kwargs={"id": self.challenge1.id})
        )
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, self.challenge1.title)

        post_res = self.client.post(
            reverse("challenges:hapus", kwargs={"id": self.challenge1.id})
        )
        self.assertEqual(post_res.status_code, 302)
        self.assertFalse(Challenge.objects.filter(id=self.challenge1.id).exists())


class ChallengeAPITests(TestCase):
    """Pengujian seluruh endpoint JSON API tantangan (/api/tantangan/)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="user_api", email="api@example.com", password="password123"
        )
        self.badge = Badge.objects.create(
            name="Pesepeda",
            requirement="Selesaikan tantangan Sepeda ke kampus.",
            icon="bike",
            tone="amber",
        )
        self.challenge = Challenge.objects.create(
            title="Sepeda ke kampus",
            description="Ganti tiga perjalanan motor dengan sepeda.",
            category=Challenge.Category.TRANSPORT,
            duration_days=2,
            points=50,
            estimated_saving_kg="2.4",
            badge=self.badge,
            icon="bike",
            tone="amber",
        )

    def test_api_requires_authentication(self):
        """Memverifikasi bahwa endpoint mengembalikan HTTP 401 saat belum terautentikasi."""
        url = reverse("challenges_api:ikut", kwargs={"id": self.challenge.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Autentikasi", response.json().get("error", ""))

    def test_api_ikut_success_dan_reject_aktif_lain(self):
        """Memverifikasi endpoint ikuti tantangan dan penolakan saat masih ada tantangan aktif."""
        self.client.force_login(self.user)
        url = reverse("challenges_api:ikut", kwargs={"id": self.challenge.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        # Coba ikuti lagi
        res_ulang = self.client.post(url)
        self.assertEqual(res_ulang.status_code, 400)
        self.assertIn("sudah kamu ikuti", res_ulang.json().get("error", ""))

    def test_api_checkin_success(self):
        """Memverifikasi check-in harian sukses via API."""
        self.client.force_login(self.user)
        Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        url = reverse("challenges_api:checkin", kwargs={"id": self.challenge.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["completed"])
        self.assertEqual(data["data"]["done_days"], 1)

    def test_api_checkin_conflict_409_on_duplicate(self):
        """Memverifikasi bahwa check-in ganda di hari yang sama menghasilkan kode status HTTP 409 Conflict."""
        self.client.force_login(self.user)
        partisipasi = Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        CheckIn.objects.create(participation=partisipasi, date=timezone.localdate())

        url = reverse("challenges_api:checkin", kwargs={"id": self.challenge.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 409)
        self.assertIn("sudah check-in hari ini", res.json().get("error", ""))

    def test_api_checkin_selesai_mendapatkan_poin_dan_badge(self):
        """Memverifikasi penyelesaian tantangan via API memberikan poin dan lencana."""
        self.client.force_login(self.user)
        partisipasi = Participation.objects.create(
            user=self.user,
            challenge=self.challenge,
            started_at=timezone.localdate() - timedelta(days=1),
        )
        CheckIn.objects.create(
            participation=partisipasi, date=timezone.localdate() - timedelta(days=1)
        )

        url = reverse("challenges_api:checkin", kwargs={"id": self.challenge.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["completed"])
        self.assertEqual(data["data"]["badge"], "Pesepeda")
        self.assertEqual(total_poin(self.user), 50)
        self.assertTrue(
            UserBadge.objects.filter(user=self.user, badge=self.badge).exists()
        )

    def test_api_berhenti_success(self):
        """Memverifikasi endpoint berhenti dari tantangan aktif."""
        self.client.force_login(self.user)
        partisipasi = Participation.objects.create(
            user=self.user, challenge=self.challenge, started_at=timezone.localdate()
        )
        url = reverse("challenges_api:berhenti", kwargs={"id": self.challenge.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        partisipasi.refresh_from_db()
        self.assertEqual(partisipasi.status, Participation.Status.STOPPED)
