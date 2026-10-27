from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import Badge, CheckIn, Participation, PointEntry, UserBadge


def total_poin(user):
    """Total poin = jumlah seluruh PointEntry milik pengguna."""
    return (
        PointEntry.objects.filter(user=user).aggregate(total=Sum("delta"))["total"] or 0
    )


def ringkasan_pengguna(user):
    """Ringkasan challenges satu pengguna, dipakai kartu profil (PR-1)."""
    status = Participation.objects.filter(user=user).values_list("status", flat=True)
    return {
        "poin": total_poin(user),
        "streak": hitung_streak(user),
        "diikuti": sum(1 for s in status if s == Participation.Status.ACTIVE),
        "selesai": sum(1 for s in status if s == Participation.Status.COMPLETED),
        "lencana": UserBadge.objects.filter(user=user).count(),
        "total_lencana": Badge.objects.count(),
    }


def sudah_checkin_hari_ini(user):
    return CheckIn.objects.filter(
        participation__user=user, date=timezone.localdate()
    ).exists()


def hitung_streak(user):
    """Hari berturut-turut sampai hari ini dengan minimal satu check-in.

    Bila hari ini belum check-in, streak masih berjalan sampai akhir hari,
    jadi penghitungan mulai dari kemarin.
    """
    tanggal_checkin = set(
        CheckIn.objects.filter(participation__user=user).values_list("date", flat=True)
    )
    hari = timezone.localdate()
    if hari not in tanggal_checkin:
        hari -= timedelta(days=1)
    streak = 0
    while hari in tanggal_checkin:
        streak += 1
        hari -= timedelta(days=1)
    return streak


def periksa_lencana_streak(user):
    """
    Memeriksa dan memberikan lencana berbasis streak harian kepada pengguna.
    - Streak 7 hari berturut-turut: Lencana 'Hijau 7 hari'
    - Streak 30 hari berturut-turut: Lencana 'Pejuang 30 hari'
    """
    streak = hitung_streak(user)
    lencana_diberikan = []

    if streak >= 7:
        badge_7_hari = Badge.objects.filter(name="Hijau 7 hari").first()
        if badge_7_hari:
            user_badge_obj, baru_dibuat = UserBadge.objects.get_or_create(
                user=user, badge=badge_7_hari
            )
            if baru_dibuat:
                lencana_diberikan.append(badge_7_hari.name)

    if streak >= 30:
        badge_30_hari = Badge.objects.filter(name="Pejuang 30 hari").first()
        if badge_30_hari:
            user_badge_obj, baru_dibuat = UserBadge.objects.get_or_create(
                user=user, badge=badge_30_hari
            )
            if baru_dibuat:
                lencana_diberikan.append(badge_30_hari.name)

    return lencana_diberikan
