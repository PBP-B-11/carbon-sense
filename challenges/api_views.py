from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Challenge, Participation
from .utils import proses_checkin


def _ambil_tantangan_atau_none(pk):
    """Mengambil objek Challenge berdasarkan primary key UUID, atau None jika tidak valid atau tidak ditemukan."""
    try:
        return Challenge.objects.filter(pk=pk).first()
    except (ValidationError, ValueError):
        return None


@require_GET
def api_daftar_tantangan(request):
    """Mengembalikan daftar seluruh tantangan dalam format JSON, mendukung filter kategori."""
    kategori = request.GET.get("kategori", "")
    qs = Challenge.objects.annotate(
        participants=Count("participations__user", distinct=True)
    ).select_related("badge")
    if kategori in Challenge.Category.values:
        qs = qs.filter(category=kategori)

    joined_ids = set()
    if request.user.is_authenticated:
        joined_ids = set(
            Participation.objects.filter(user=request.user).values_list(
                "challenge_id", flat=True
            )
        )

    data = [
        {
            "id": str(c.id),
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "category_display": c.get_category_display(),
            "duration_days": c.duration_days,
            "points": c.points,
            "estimated_saving_kg": float(c.estimated_saving_kg),
            "badge": c.badge.name if c.badge else None,
            "icon": c.icon,
            "tone": c.tone,
            "participants": c.participants,
            "is_joined": c.id in joined_ids,
        }
        for c in qs
    ]
    return JsonResponse(data, safe=False)


@require_GET
def api_detail_tantangan(request, id):
    """Mengembalikan detail satu tantangan dalam format JSON."""
    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    participants_count = (
        Participation.objects.filter(challenge=challenge)
        .values("user")
        .distinct()
        .count()
    )
    return JsonResponse(
        {
            "id": str(challenge.id),
            "title": challenge.title,
            "description": challenge.description,
            "category": challenge.category,
            "category_display": challenge.get_category_display(),
            "duration_days": challenge.duration_days,
            "points": challenge.points,
            "estimated_saving_kg": float(challenge.estimated_saving_kg),
            "badge": challenge.badge.name if challenge.badge else None,
            "icon": challenge.icon,
            "tone": challenge.tone,
            "participants": participants_count,
        }
    )


@require_POST
def api_ikuti(request, id):
    """Endpoint JSON untuk mendaftarkan pengguna mengikuti sebuah tantangan."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)

    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    partisipasi_aktif = (
        Participation.objects.filter(
            user=request.user, status=Participation.Status.ACTIVE
        )
        .select_related("challenge")
        .first()
    )

    if partisipasi_aktif:
        if partisipasi_aktif.challenge_id == challenge.id:
            return JsonResponse(
                {"error": "Tantangan ini sudah kamu ikuti."}, status=400
            )
        return JsonResponse(
            {
                "error": (
                    f'Kamu masih memiliki tantangan aktif: "{partisipasi_aktif.challenge.title}". '
                    "Selesaikan atau batalkan tantangan tersebut terlebih dahulu."
                )
            },
            status=400,
        )

    partisipasi = Participation.objects.create(
        user=request.user,
        challenge=challenge,
        started_at=timezone.localdate(),
        status=Participation.Status.ACTIVE,
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
        user=request.user, challenge=challenge, status=Participation.Status.ACTIVE
    ).first()
    if partisipasi is None:
        return JsonResponse(
            {"error": "Kamu belum mengikuti tantangan ini."}, status=404
        )

    hasil = proses_checkin(partisipasi, request.user)
    if not hasil["baru_dibuat"]:
        return JsonResponse({"error": "Kamu sudah check-in hari ini."}, status=409)

    if hasil["selesai"]:
        pesan = f'Selamat, "{challenge.title}" selesai! +{challenge.points} poin.'
    else:
        pesan = "Check-in hari ini tercatat."

    return JsonResponse(
        {
            "status": "success",
            "completed": hasil["selesai"],
            "message": pesan,
            "data": {
                "done_days": hasil["progres"]["done_days"],
                "total_days": hasil["progres"]["total_days"],
                "percent": hasil["progres"]["percent"],
                "points_earned": hasil["points_earned"],
                "total_points": hasil["total_points"],
                "streak": hasil["streak"],
                "badge": hasil["lencana_tantangan"],
                "streak_badges": hasil["lencana_streak"],
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
        user=request.user, challenge=challenge, status=Participation.Status.ACTIVE
    ).update(status=Participation.Status.STOPPED)

    if not baris_terubah:
        return JsonResponse(
            {"error": "Kamu belum mengikuti tantangan ini."}, status=400
        )

    return JsonResponse(
        {
            "status": "success",
            "message": f'Kamu berhenti dari "{challenge.title}".',
        },
        status=200,
    )


@require_POST
def api_hapus(request, id):
    """Endpoint JSON untuk menghapus tantangan dari katalog (khusus superuser)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)
    if not request.user.is_superuser:
        return JsonResponse(
            {"error": "Hanya superuser yang dapat menghapus tantangan."}, status=403
        )

    challenge = _ambil_tantangan_atau_none(id)
    if challenge is None:
        return JsonResponse({"error": "Tantangan tidak ditemukan."}, status=404)

    judul = challenge.title
    challenge.delete()
    return JsonResponse(
        {
            "status": "success",
            "message": f'Tantangan "{judul}" berhasil dihapus.',
        },
        status=200,
    )
