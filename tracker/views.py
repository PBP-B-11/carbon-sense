from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .activity_actions import process_activity_form
from .dashboard import build_dashboard_context
from .forms import CarbonActivityForm
from .models import CarbonActivity

from django.http import JsonResponse


def index(request, pk=None):
    # Ambil aktivitas edit hanya jika pengguna adalah pemiliknya
    editing_activity = None
    if pk is not None:
        if not request.user.is_authenticated:
            messages.error(request, "Silakan login untuk mengedit aktivitas.")
            return redirect("tracker:index")
        editing_activity = get_object_or_404(
            CarbonActivity,
            pk=pk,
            user=request.user,
        )

    # Siapkan formulir untuk aktivitas baru atau aktivitas yang sedang diedit
    form = CarbonActivityForm(
        request.POST if request.method == "POST" else None,
        instance=editing_activity,
    )
    estimate = None

    # Serahkan validasi, estimasi, dan penyimpanan kepada fungsi khusus aktivitas
    if request.method == "POST":
        estimate, saved_activity = process_activity_form(
            form,
            request.user,
            saving=request.POST.get("action") == "save",
        )
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        # Kembalikan estimasi atau hasil penyimpanan untuk permintaan AJAX.
        if is_ajax:
            errors = form.errors.get_json_data()
            response_data = {
                "estimate": estimate,
                "errors": errors,
            }

            # Berikan identitas aktivitas dan pesan setelah berhasil disimpan.
            if saved_activity is not None:
                response_data.update(
                    {
                        "activity_id": saved_activity.pk,
                        "message": "Aktivitas berhasil disimpan.",
                    }
                )

            return JsonResponse(
                response_data,
                status=400 if errors else 200,
            )

        # Pertahankan pengalihan setelah penyimpanan formulir tanpa AJAX.
        if saved_activity is not None:
            messages.success(request, "Aktivitas berhasil disimpan.")
            return redirect("tracker:index")

    # Batasi riwayat dan seluruh perhitungan dashboard pada pengguna saat ini
    activities = CarbonActivity.objects.none()
    if request.user.is_authenticated:
        activities = CarbonActivity.objects.filter(user=request.user).order_by(
            "-date", "-pk"
        )

    # Siapkan ringkasan, kategori, dan grafik melalui fungsi khusus dashboar
    context = build_dashboard_context(
        activities,
        request.GET.get("period", "week"),
        timezone.localdate(),
    )
    context.update(
        {
            "form": form,
            "estimate": estimate,
            "activities": activities,
            "editing_activity": editing_activity,
        }
    )
    return render(request, "tracker/tracker.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def delete_activity(request, pk):
    activity = get_object_or_404(
        CarbonActivity,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        # Simpan ID sebelum Django mengosongkan pk setelah penghapusan.
        activity_id = activity.pk
        activity.delete()

        # Kembalikan konfirmasi untuk AJAX tanpa mengubah alur formulir biasa.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "activity_id": activity_id,
                    "message": "Aktivitas berhasil dihapus.",
                }
            )

        messages.success(request, "Aktivitas berhasil dihapus.")
        return redirect("tracker:index")

    return render(
        request,
        "tracker/activity_confirm_delete.html",
        {"activity": activity},
    )
