from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import TantanganForm
from .models import Badge, Challenge, CheckIn, Participation, PointEntry, UserBadge
from .utils import hitung_streak, periksa_lencana_streak, sudah_checkin_hari_ini, total_poin


def hitung_progres(partisipasi):
    selesai = partisipasi.check_ins.count()
    total = partisipasi.challenge.duration_days
    return {
        "done_days": selesai,
        "total_days": total,
        "percent": min(selesai * 100 // total, 100) if total else 0,
    }


def ikuti(request, tantangan):
    """Mendaftarkan pengguna mengikuti tantangan baru jika belum memiliki tantangan aktif."""
    partisipasi_aktif = Participation.objects.filter(
        user=request.user, status=Participation.Status.ACTIVE
    ).select_related("challenge").first()

    if partisipasi_aktif:
        if partisipasi_aktif.challenge_id == tantangan.id:
            messages.warning(request, "Tantangan ini sudah kamu ikuti.")
        else:
            messages.warning(
                request,
                f'Kamu masih memiliki tantangan aktif: "{partisipasi_aktif.challenge.title}". '
                "Selesaikan atau batalkan tantangan tersebut terlebih dahulu."
            )
        return

    Participation.objects.create(
        user=request.user, challenge=tantangan, started_at=timezone.localdate()
    )
    messages.success(request, f'Kamu mengikuti "{tantangan.title}".')


def checkin(request, tantangan):
    """Mencatat check-in harian untuk tantangan aktif melalui form submission."""
    partisipasi = Participation.objects.filter(
        user=request.user, challenge=tantangan, status=Participation.Status.ACTIVE
    ).first()
    if partisipasi is None:
        messages.error(request, "Kamu belum mengikuti tantangan ini.")
        return

    with transaction.atomic():
        checkin_objek, baru_dibuat = partisipasi.check_ins.get_or_create(date=timezone.localdate())
        if not baru_dibuat:
            messages.warning(request, "Kamu sudah check-in hari ini.")
            return

        periksa_lencana_streak(request.user)
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
def tambah_tantangan(request):
    """Halaman tambah tantangan, dibatasi khusus untuk superuser."""
    if not request.user.is_superuser:
        raise PermissionDenied("Hanya superuser yang dapat menambahkan tantangan baru.")

    form = TantanganForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        tantangan = form.save()
        messages.success(request, f'Tantangan "{tantangan.title}" ditambahkan.')
        return redirect("challenges:index")
    return render(request, "challenges/tambah.html", {"form": form})


@login_required
def ubah_tantangan(request, id):
    """Halaman ubah tantangan, dibatasi khusus untuk superuser."""
    if not request.user.is_superuser:
        raise PermissionDenied("Hanya superuser yang dapat mengubah tantangan.")

    tantangan = get_object_or_404(Challenge, pk=id)
    form = TantanganForm(request.POST or None, instance=tantangan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Tantangan "{tantangan.title}" berhasil diperbarui.')
        return redirect("challenges:index")
    return render(request, "challenges/ubah.html", {"form": form, "challenge": tantangan})


@login_required
def hapus_tantangan(request, id):
    """Menghapus tantangan dari katalog, dibatasi khusus untuk superuser."""
    if not request.user.is_superuser:
        raise PermissionDenied("Hanya superuser yang dapat menghapus tantangan.")

    tantangan = get_object_or_404(Challenge, pk=id)
    if request.method == "POST":
        judul = tantangan.title
        tantangan.delete()
        messages.success(request, f'Tantangan "{judul}" berhasil dihapus.')
        return redirect("challenges:index")

    return render(request, "challenges/hapus.html", {"challenge": tantangan})


def daftar_tantangan(request):
    """Menampilkan katalog tantangan publik dan progres pribadi pengguna terautentikasi."""
    user = request.user

    if request.method == "POST":
        if not user.is_authenticated:
            return redirect(f"{reverse('profil:login')}?next={request.path}")
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

    kartu_aktif = None
    joined_ids = set()
    lencana_dimiliki = set()
    streak = 0
    streak_at_risk = False
    poin_total = 0

    if user.is_authenticated:
        aktif = (
            Participation.objects.filter(user=user, status=Participation.Status.ACTIVE)
            .select_related("challenge")
            .order_by("-started_at")
        )
        lencana_dimiliki = set(
            UserBadge.objects.filter(user=user).values_list("badge_id", flat=True)
        )
        streak = hitung_streak(user)
        hari_ini = timezone.localdate()
        ada_checkin_hari_ini = CheckIn.objects.filter(
            participation__user=user, date=hari_ini
        ).exists()

        pertama = aktif.first()
        if pertama:
            progres = hitung_progres(pertama)
            sudah_checkin_partisipasi = pertama.check_ins.filter(date=hari_ini).exists()
            titik = ["done"] * progres["done_days"]
            if progres["done_days"] < progres["total_days"]:
                titik.append("todo" if sudah_checkin_partisipasi else "today")
            titik += ["todo"] * (progres["total_days"] - len(titik))
            kartu_aktif = {
                "participation": pertama,
                "challenge": pertama.challenge,
                "checked_today": sudah_checkin_partisipasi,
                "dots": titik,
                "sisa_hari": progres["total_days"] - progres["done_days"],
                **progres,
            }
        joined_ids = set(aktif.values_list("challenge_id", flat=True))
        streak_at_risk = streak > 0 and not ada_checkin_hari_ini
        poin_total = total_poin(user)

    context = {
        "challenges": tantangan,
        "categories": Challenge.Category.choices,
        "selected_category": kategori,
        "joined_ids": joined_ids,
        "badges": Badge.objects.all(),
        "owned_badge_ids": lencana_dimiliki,
        "owned_badge_count": len(lencana_dimiliki),
        "total_points": poin_total,
        "streak": streak,
        "streak_at_risk": streak_at_risk,
        "active": kartu_aktif,
    }
    return render(request, "challenges/challenges.html", context)
