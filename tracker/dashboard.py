from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum


#Gunakan nol desimal saat tidak ada aktivitas dalam suatu rentang.
def sum_emissions(activities):
    return activities.aggregate(total=Sum("emission_kg", default=Decimal("0")))["total"]


def build_category_breakdown(activities, total):
    #Jumlahkan aktivitas menurut jenis, lalu gabungkan ayam dan sapi sebagai Daging.
    rows = activities.order_by().values("activity_type").annotate(total=Sum("emission_kg"))
    totals_by_type = {row["activity_type"]: row["total"] for row in rows}
    categories = [
        (("car_travel",), "Transportasi", "i-car"),
        (("electricity",), "Listrik", "i-zap"),
        (("chicken", "beef"), "Daging", "i-utensils"),
    ]
    breakdown = []
    for kinds, label, icon in categories:
        emissions = sum((totals_by_type.get(kind, Decimal("0")) for kind in kinds), Decimal("0"))
        breakdown.append({
            "label": label,
            "icon": icon,
            "emissions": emissions,
            "percentage": emissions / total * Decimal("100") if total else Decimal("0"),
        })
    return breakdown


def build_dashboard_context(activities, period, today):
    """Prepare dashboard data from the current user's activity queryset."""
    #Validasi pilihan periode dan tentukan tanggal awalnya.
    week_start = today - timedelta(days=today.weekday())
    periods = {
        "week": (week_start, "Minggu ini"),
        "month": (today.replace(day=1), "Bulan ini"),
        "year": (today.replace(month=1, day=1), "Tahun ini"),
    }
    if period not in periods:
        period = "week"
    period_start, period_label = periods[period]
    period_activities = activities.filter(date__range=(period_start, today))
    period_emissions = sum_emissions(period_activities)

    #Hitung rincian kategori dan sumber terbesar untuk periode yang sama.
    category_breakdown = build_category_breakdown(period_activities, period_emissions)
    top_category = (
        max(category_breakdown, key=lambda category: category["emissions"])
        if period_emissions else None
    )

    #Ringkasan hari ini dan rata-rata tujuh hari tetap terpisah dari filter periode.
    seven_days_start = today - timedelta(days=6)
    return {
        "total_emissions": sum_emissions(activities),
        "today_emissions": sum_emissions(activities.filter(date=today)),
        "week_emissions": sum_emissions(activities.filter(date__range=(week_start, today))),
        "average_daily_emissions": sum_emissions(
            activities.filter(date__range=(seven_days_start, today))
        ) / Decimal("7"),
        "period": period,
        "period_label": period_label,
        "period_emissions": period_emissions,
        "category_breakdown": category_breakdown,
        "top_category": top_category,
        "daily_chart": build_emissions_chart(period_activities, period, today),
    }


def build_emissions_chart(activities, period, today):
    """Build chart bars from a queryset already scoped to the current user."""
    #Siapkan tanggal dan label untuk seluruh minggu, bulan, atau tahun.
    day_labels = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    month_labels = [
        "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
        "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
    ]
    if period == "year":
        dates = [today.replace(month=month, day=1) for month in range(1, 13)]
        labels = month_labels
        group_field = "date__month"
    elif period == "month":
        days_in_month = monthrange(today.year, today.month)[1]
        dates = [today.replace(day=day) for day in range(1, days_in_month + 1)]
        labels = [str(day.day) for day in dates]
        group_field = "date"
    else:
        week_start = today - timedelta(days=today.weekday())
        dates = [week_start + timedelta(days=offset) for offset in range(7)]
        labels = day_labels
        group_field = "date"

    #Batasi data sampai hari ini dan jumlahkan emisi per hari atau per bulan.
    totals = (
        activities.filter(date__range=(dates[0], today))
        .order_by()
        .values(group_field)
        .annotate(total=Sum("emission_kg"))
    )
    totals_by_bucket = {row[group_field]: row["total"] for row in totals}
    highest = max(totals_by_bucket.values(), default=Decimal("0"))

    #Isi interval kosong dengan nol dan tandai interval yang belum berlangsung.
    chart = []
    for day, label in zip(dates, labels):
        bucket = day.month if period == "year" else day
        emissions = totals_by_bucket.get(bucket, Decimal("0"))
        chart.append({
            "date": day,
            "label": label,
            "emissions": emissions,
            "height": max(4, int(emissions / highest * 190)) if highest else 4,
            "is_future": day > today,
        })
    return chart
