from decimal import Decimal

from django.db.models import Sum
from .models import CarbonActivity

import requests
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CarbonActivityForm
from .services import estimate_car_travel, estimate_electricity

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from datetime import timedelta
from django.utils import timezone

def index(request, pk=None):
    #Load aktivitas dan verify owner
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

    #Prare form
    form = CarbonActivityForm(
        request.POST if request.method == "POST" else None,
        instance=editing_activity,
    )

    #Prepare estimation
    estimate = None
    saving = request.POST.get("action") == "save"

    #Validasi data
    if request.method == "POST" and form.is_valid():
        if saving and not request.user.is_authenticated:
            form.add_error(None, "Silakan login untuk menyimpan aktivitas.")
#Izinkan aktivitas yang sudah memiliki kalkulasi.
        elif form.cleaned_data["activity_type"] not in (
            "electricity", "car_travel"
        ):
            form.add_error(
                "activity_type",
                "Perhitungan makanan belum tersedia.",
            )
        else:
            #Request emissions dari climatiq
            try:
                quantity = form.cleaned_data["quantity"]

                if form.cleaned_data["activity_type"] == "electricity":
                    estimate = estimate_electricity(quantity)
                else:
                    estimate = estimate_car_travel(quantity)
            except (requests.RequestException, ValueError):
                form.add_error(None, "Gagal menghitung emisi. Coba lagi.")
            else:
                #Save the activity untuk owner
                if saving:
                    activity = form.save(commit=False)
                    activity.user = request.user
                    activity.emission_kg = Decimal(
                        str(estimate["co2e"])
                    ).quantize(Decimal("0.0001"))
                    activity.save()

                    #Confirm saving
                    messages.success(request, "Aktivitas berhasil disimpan.")
                    return redirect("tracker:index")

    #Load user history
    activities = CarbonActivity.objects.none()


    if request.user.is_authenticated:
        activities = CarbonActivity.objects.filter(
            user=request.user
        ).order_by("-date", "-pk")

    #Kalkulasi total emisi
    total_emissions = activities.aggregate(
        total=Sum("emission_kg", default=Decimal("0"))
    )["total"]

    #Definisikan hari berdasarkan timezone
    today = timezone.localdate()

    week_start = today - timedelta(days=today.weekday())
    seven_days_start = today - timedelta(days=6)

    #Kalkulasi emisi hari ini
    today_emissions = activities.filter(date=today).aggregate(
        total=Sum("emission_kg", default=Decimal("0"))
    )["total"]

    #Kalkulasi emisi minggu ini
    week_emissions = activities.filter(
        date__range=(week_start, today)
    ).aggregate(
        total=Sum("emission_kg", default=Decimal("0"))
    )["total"]

    #Kalkulasi rata rata
    seven_days_emissions = activities.filter(
        date__range=(seven_days_start, today)
    ).aggregate(
        total=Sum("emission_kg", default=Decimal("0"))
    )["total"]

    average_daily_emissions = seven_days_emissions / Decimal("7")


    daily_totals = (
        activities.filter(date__range=(week_start, today))
        .order_by()
        .values("date")
        .annotate(total=Sum("emission_kg"))
    )

    #Index total perhari
    totals_by_date = {
        row["date"]: row["total"] for row in daily_totals
    }

    #Siapkan chart
    highest = max(totals_by_date.values(), default=Decimal("0"))
    day_labels = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    daily_chart = []

    #week bar
    for index in range(7):
        day = week_start + timedelta(days=index)
        emissions = totals_by_date.get(day, Decimal("0"))

        #skala bar pada frontend
        height = (
            max(4, int(emissions / highest * 190))
            if highest
            else 4
        )

        daily_chart.append({
            "date": day,
            "label": day_labels[index],
            "emissions": emissions,
            "height": height,
            "is_future": day > today,
        })

    #Jumlahkan emisi minggu ini 
    category_totals = (
        activities.filter(date__range=(week_start, today))
        .order_by()
        .values("activity_type")
        .annotate(total=Sum("emission_kg"))
    )

    totals_by_type = {
        row["activity_type"]: row["total"]
        for row in category_totals
    }

    categories = [
        ("car_travel", "Transportasi", "i-car"),
        ("electricity", "Listrik", "i-zap"),
        ("meal", "Makanan", "i-utensils"),
    ]
    category_breakdown = []

    for activity_type, label, icon in categories:
        emissions = totals_by_type.get(activity_type, Decimal("0"))
        percentage = (
            emissions / week_emissions * Decimal("100")
            if week_emissions
            else Decimal("0")
        )

        category_breakdown.append({
            "label": label,
            "icon": icon,
            "emissions": emissions,
            "percentage": percentage,
        })

    #Pilih kategori dengan emisi 
    top_category = (
        max(category_breakdown, key=lambda category: category["emissions"])
        if week_emissions
        else None
    )
    
    #Pass form
    return render(
    request,
    "tracker/tracker.html",
    {
        "form": form,
        "estimate": estimate,
        "activities": activities,
        "total_emissions": total_emissions,
        "editing_activity": editing_activity,
        "today_emissions": today_emissions,
        "week_emissions": week_emissions,
        "average_daily_emissions": average_daily_emissions,
        "daily_chart": daily_chart,
        "category_breakdown": category_breakdown,
        "top_category": top_category,
    },
)

@login_required
@require_http_methods(["GET", "POST"])
def delete_activity(request, pk):
    activity = get_object_or_404(
        CarbonActivity,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        activity.delete()
        messages.success(request, "Aktivitas berhasil dihapus.")
        return redirect("tracker:index")

    return render(
        request,
        "tracker/activity_confirm_delete.html",
        {"activity": activity},
    )
