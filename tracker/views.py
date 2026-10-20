import requests
from django.shortcuts import render

from .forms import CarbonActivityForm
from .services import estimate_electricity


def index(request):
    form = CarbonActivityForm(
        request.POST if request.method == "POST" else None
    )
    estimate = None

    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["activity_type"] == "electricity":
            try:
                estimate = estimate_electricity(
                    form.cleaned_data["quantity"]
                )
            except (requests.RequestException, ValueError):
                form.add_error(
                    None, "Gagal menghitung emisi. Silakan coba lagi."
                )
        else:
            form.add_error(
                "activity_type",
                "Saat ini perhitungan tersedia untuk listrik saja.",
            )

    return render(
        request,
        "tracker/tracker.html",
        {"form": form, "estimate": estimate},
    )