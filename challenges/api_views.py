from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Challenge, Participation, PointEntry, UserBadge
from .utils import hitung_streak, periksa_lencana_streak, total_poin
from .views import hitung_progres


def _ambil_tantangan_atau_none(pk):
    """Mengambil objek Challenge berdasarkan primary key UUID, atau None jika tidak valid."""
    try:
        return get_object_or_404(Challenge, pk=pk)
    except (ValidationError, ValueError):
        return None


@require_POST
def api_ikuti(request, id):
    """Endpoint JSON untuk mendaftarkan pengguna mengikuti sebuah tantangan."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)

    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    sudah_ikut = Participation.objects.filter(
        user=request.user,
        challenge=challenge,
        status=Participation.Status.ACTIVE
    ).exists()
    if sudah_ikut:
        return JsonResponse({"error": "Tantangan ini sudah kamu ikuti."}, status=400)

    partisipasi = Participation.objects.create(
        user=request.user,
        challenge=challenge,
        started_at=timezone.localdate(),
        status=Participation.Status.ACTIVE
    )

    return JsonResponse(
        {
            "status": "success",
            "message": f'Kamu mengikuti "{challenge.title}".',
            "data": {
                "participation_id": str(partisipasi.id),
                "challenge_id": str(challenge.id),
                "title": challenge.title,
                "started_at": str(partisipasi.started_at),
            },
        },
        status=200,
    )


@require_POST
def api_checkin(request, id):
    """Endpoint JSON untuk mencatat check-in harian tantangan aktif pengguna."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)

    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    partisipasi = Participation.objects.filter(
        user=request.user,
        challenge=challenge,
        status=Participation.Status.ACTIVE
    ).first()
    if partisipasi is None:
        return JsonResponse({"error": "Kamu belum mengikuti tantangan ini."}, status=404)

    with transaction.atomic():
        hari_ini = timezone.localdate()
        checkin_objek, baru_dibuat = partisipasi.check_ins.get_or_create(date=hari_ini)
        if not baru_dibuat:
            return JsonResponse({"error": "Kamu sudah check-in hari ini."}, status=409)

        lencana_streak = periksa_lencana_streak(request.user)
        progres = hitung_progres(partisipasi)

        if progres["done_days"] >= progres["total_days"]:
            partisipasi.status = Participation.Status.COMPLETED
            partisipasi.save(update_fields=["status"])

            PointEntry.objects.create(
                user=request.user,
                delta=challenge.points,
                reason=f'Menyelesaikan "{challenge.title}"',
            )

            lencana_tantangan = None
            if challenge.badge:
                user_badge_obj, badge_baru = UserBadge.objects.get_or_create(
                    user=request.user, badge=challenge.badge
                )
                lencana_tantangan = challenge.badge.name

            return JsonResponse(
                {
                    "status": "success",
                    "completed": True,
                    "message": f'Selamat, "{challenge.title}" selesai! +{challenge.points} poin.',
                    "data": {
                        "done_days": progres["done_days"],
                        "total_days": progres["total_days"],
                        "percent": progres["percent"],
                        "points_earned": challenge.points,
                        "total_points": total_poin(request.user),
                        "streak": hitung_streak(request.user),
                        "badge": lencana_tantangan,
                        "streak_badges": lencana_streak,
                    },
                },
                status=200,
            )

        return JsonResponse(
            {
                "status": "success",
                "completed": False,
                "message": "Check-in hari ini tercatat.",
                "data": {
                    "done_days": progres["done_days"],
                    "total_days": progres["total_days"],
                    "percent": progres["percent"],
                    "total_points": total_poin(request.user),
                    "streak": hitung_streak(request.user),
                    "streak_badges": lencana_streak,
                },
            },
            status=200,
        )


@require_POST
def api_berhenti(request, id):
    """Endpoint JSON untuk berhenti dari tantangan aktif yang sedang diikuti."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)

    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    baris_terubah = Participation.objects.filter(
        user=request.user,
        challenge=challenge,
        status=Participation.Status.ACTIVE
    ).update(status=Participation.Status.STOPPED)

    if not baris_terubah:
        return JsonResponse({"error": "Kamu belum mengikuti tantangan ini."}, status=400)

    return JsonResponse(
        {
            "status": "success",
            "message": f'Kamu berhenti dari "{challenge.title}".',
        },
        status=200,
    )
