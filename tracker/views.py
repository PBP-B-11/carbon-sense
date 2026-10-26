from decimal import Decimal

from django.db.models import Sum
from .models import CarbonActivity

import requests
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import CarbonActivityForm
from .services import estimate_electricity


def index(request):
    form = CarbonActivityForm(
        request.POST if request.method == "POST" else None
    )
    estimate = None
    saving = request.POST.get("action") == "save"

    if request.method == "POST" and form.is_valid():
        if saving and not request.user.is_authenticated:
            form.add_error(None, "Silakan login untuk menyimpan aktivitas.")
        elif form.cleaned_data["activity_type"] != "electricity":
            form.add_error(
                "activity_type",
                "Saat ini perhitungan tersedia untuk listrik saja.",
            )
        else:
            try:
                estimate = estimate_electricity(
                    form.cleaned_data["quantity"]
                )
            except (requests.RequestException, ValueError):
                form.add_error(None, "Gagal menghitung emisi. Coba lagi.")
            else:
                if saving:
                    activity = form.save(commit=False)
                    activity.user = request.user
                    activity.emission_kg = Decimal(
                        str(estimate["co2e"])
                    ).quantize(Decimal("0.0001"))
                    activity.save()

                    messages.success(request, "Aktivitas berhasil disimpan.")
                    return redirect("tracker:index")

    activities = CarbonActivity.objects.none()

    if request.user.is_authenticated:
        activities = CarbonActivity.objects.filter(
            user=request.user
        ).order_by("-date", "-pk")

    total_emissions = activities.aggregate(
        total=Sum("emission_kg", default=Decimal("0"))
    )["total"]
    
    return render(
    request,
    "tracker/tracker.html",
    {
        "form": form,
        "estimate": estimate,
        "activities": activities,
        "total_emissions": total_emissions,
    },
)