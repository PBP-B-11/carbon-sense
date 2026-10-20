from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Badge, Challenge, Participation, PointEntry, UserBadge
from .utils import hitung_streak, sudah_checkin_hari_ini, total_poin


def hitung_progres(partisipasi):
    selesai = partisipasi.check_ins.count()
    total = partisipasi.challenge.duration_days
    return {
        "done_days": selesai,
        "total_days": total,
        "percent": min(selesai * 100 // total, 100) if total else 0,
    }


def ikuti(request, tantangan):
    sudah_ikut = Participation.objects.filter(
        user=request.user, challenge=tantangan, status=Participation.Status.ACTIVE
    ).exists()
    if sudah_ikut:
        messages.warning(request, "Tantangan ini sudah kamu ikuti.")
        return
    Participation.objects.create(
        user=request.user, challenge=tantangan, started_at=timezone.localdate()
    )
    messages.success(request, f'Kamu mengikuti "{tantangan.title}".')


def checkin(request, tantangan):
    partisipasi = Participation.objects.filter(
        user=request.user, challenge=tantangan, status=Participation.Status.ACTIVE
    ).first()
    if partisipasi is None:
        messages.error(request, "Kamu belum mengikuti tantangan ini.")
        return

    with transaction.atomic():
        _, dibuat = partisipasi.check_ins.get_or_create(date=timezone.localdate())
        if not dibuat:
            messages.warning(request, "Kamu sudah check-in hari ini.")
            return

        progres = hitung_progres(partisipasi)
        if progres["done_days"] >= progres["total_days"]:
            partisipasi.status = Participation.Status.COMPLETED
            partisipasi.save(update_fields=["status"])
            PointEntry.objects.create(
                user=request.user,
                delta=tantangan.points,
                reason=f'Menyelesaikan "{tantangan.title}"',
            )
            if tantangan.badge:
                UserBadge.objects.get_or_create(user=request.user, badge=tantangan.badge)
            messages.success(
                request, f'Selamat, "{tantangan.title}" selesai! +{tantangan.points} poin.'
            )
        else:
            messages.success(request, "Check-in hari ini tercatat.")


def berhenti(request, tantangan):
    updated = Participation.objects.filter(
        user=request.user, challenge=tantangan, status=Participation.Status.ACTIVE
    ).update(status=Participation.Status.STOPPED)
    if updated:
        messages.success(request, f'Kamu berhenti dari "{tantangan.title}".')
    else:
        messages.error(request, "Kamu belum mengikuti tantangan ini.")


AKSI = {"ikut": ikuti, "checkin": checkin, "berhenti": berhenti}


@login_required
def daftar_tantangan(request):
    user = request.user

    if request.method == "POST":
        aksi = AKSI.get(request.POST.get("aksi"))
        if aksi is None:
            messages.error(request, "Aksi tidak dikenal.")
        else:
            try:
                tantangan = get_object_or_404(Challenge, pk=request.POST.get("tantangan_id"))
            except ValidationError:
                raise Http404("Tantangan tidak ditemukan.")
            aksi(request, tantangan)
        return redirect("challenges:index")

    kategori = request.GET.get("kategori", "")
    tantangan = Challenge.objects.annotate(
        participants=Count("participations__user", distinct=True)
    )
    if kategori in Challenge.Category.values:
        tantangan = tantangan.filter(category=kategori)

    aktif = (
        Participation.objects.filter(user=user, status=Participation.Status.ACTIVE)
        .select_related("challenge")
        .order_by("-started_at")
    )
    lencana_dimiliki = set(
        UserBadge.objects.filter(user=user).values_list("badge_id", flat=True)
    )
    streak = hitung_streak(user)
    sudah_checkin_sekarang = sudah_checkin_hari_ini(user)

    kartu_aktif = None
    pertama = aktif.first()
    if pertama:
        progres = hitung_progres(pertama)
        titik = ["done"] * progres["done_days"]
        if progres["done_days"] < progres["total_days"]:
            titik.append("todo" if sudah_checkin_sekarang else "today")
        titik += ["todo"] * (progres["total_days"] - len(titik))
        kartu_aktif = {
            "participation": pertama,
            "challenge": pertama.challenge,
            "checked_today": sudah_checkin_sekarang,
            "dots": titik,
            "sisa_hari": progres["total_days"] - progres["done_days"],
            **progres,
        }

    context = {
        "challenges": tantangan,
        "categories": Challenge.Category.choices,
        "selected_category": kategori,
        "joined_ids": set(aktif.values_list("challenge_id", flat=True)),
        "badges": Badge.objects.all(),
        "owned_badge_ids": lencana_dimiliki,
        "owned_badge_count": len(lencana_dimiliki),
        "total_points": total_poin(user),
        "streak": streak,
        "streak_at_risk": streak > 0 and not sudah_checkin_sekarang,
        "active": kartu_aktif,
    }
    return render(request, "challenges/challenges.html", context)
