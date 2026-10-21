import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Tone(models.TextChoices):
    """Warna ikon bulat pada kartu (kelas CSS tone-*)."""

    MOSS = "moss", "Moss"
    TEAL = "teal", "Teal"
    AMBER = "amber", "Amber"


class Badge(models.Model):
    """Lencana. Delapan lencana pada desain; yang belum dimiliki tampil terkunci."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, unique=True)
    requirement = models.CharField(max_length=200, help_text="Syarat memperoleh lencana")
    icon = models.CharField(max_length=40, help_text="Nama simbol SVG, mis. train-front")
    tone = models.CharField(max_length=10, choices=Tone.choices, default=Tone.MOSS)

    def __str__(self):
        return self.name


class Challenge(models.Model):
    """Katalog tantangan."""

    class Category(models.TextChoices):
        TRANSPORT = "transportasi", "Transportasi"
        ENERGY = "energi", "Energi"
        FOOD = "makanan", "Makanan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    duration_days = models.PositiveIntegerField(default=7)
    points = models.PositiveIntegerField(default=0, help_text="Hadiah poin saat selesai")
    estimated_saving_kg = models.DecimalField(
        max_digits=6, decimal_places=1, default=0, help_text="Perkiraan emisi yang dihemat (kg CO2e)"
    )
    badge = models.ForeignKey(
        Badge, null=True, blank=True, on_delete=models.SET_NULL, related_name="challenges"
    )
    icon = models.CharField(max_length=40, help_text="Nama simbol SVG, mis. bike")
    tone = models.CharField(max_length=10, choices=Tone.choices, default=Tone.AMBER)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Participation(models.Model):
    """Pengguna mengikuti sebuah tantangan (Ikuti, Berhenti, selesai)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        COMPLETED = "completed", "Selesai"
        STOPPED = "stopped", "Berhenti"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations"
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="participations"
    )
    started_at = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            # Unik per pengguna dan tantangan yang masih aktif
            models.UniqueConstraint(
                fields=["user", "challenge"],
                condition=Q(status="active"),
                name="unique_active_participation",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.challenge} ({self.status})"


class CheckIn(models.Model):
    """Check-in harian. Unik per partisipasi dan tanggal, mencegah check-in ganda."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participation = models.ForeignKey(
        Participation, on_delete=models.CASCADE, related_name="check_ins"
    )
    date = models.DateField()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["participation", "date"], name="unique_check_in_per_day"
            ),
        ]

    def __str__(self):
        return f"{self.participation} @ {self.date}"


class UserBadge(models.Model):
    """Lencana yang sudah diperoleh pengguna."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_badges"
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="owners")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-earned_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "badge"], name="unique_badge_per_user"),
        ]

    def __str__(self):
        return f"{self.user} - {self.badge}"


class PointEntry(models.Model):
    """Buku besar poin. Total poin pengguna = jumlah seluruh baris (tidak disimpan sebagai angka)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="point_entries"
    )
    delta = models.IntegerField(help_text="Selisih poin, positif atau negatif")
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "point entries"

    def __str__(self):
        return f"{self.user} {self.delta:+d} ({self.reason})"
