from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.timesince import timesince

from challenges.models import Challenge
from community.news import fetch_news
from tracker.models import CarbonActivity

FALLBACK_NEWS = [
    {
        "title": "Kurangi Emisi Harian: Langkah Kecil Menuju Kota Rendah Karbon",
        "source": "Kementerian Lingkungan Hidup",
        "url": "/community/",
        "time_str": "Baru saja",
    },
    {
        "title": "Transportasi Publik dan Efisiensi Energi di Kawasan Perkotaan",
        "source": "Bappenas",
        "url": "/community/",
        "time_str": "Hari ini",
    },
    {
        "title": "Membiasakan Pola Konsumsi Berkelanjutan untuk Bumi yang Lebih Sejuk",
        "source": "Carbon Sense News",
        "url": "/community/",
        "time_str": "Kemarin",
    },
]


def index(request):
    """Halaman utama (Beranda) yang mengintegrasikan data dinamis dari seluruh modul."""
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    # 1. Total emisi minggu ini dari Modul Tracker
    if request.user.is_authenticated:
        total_emission = CarbonActivity.objects.filter(
            user=request.user, date__range=(week_start, today)
        ).aggregate(total=Sum("emission_kg"))["total"] or Decimal("0")
    else:
        total_emission = Decimal("0")

    # 2. Tips hari ini dari Modul Eco-Challenges
    featured_tip = (
        Challenge.objects.filter(estimated_saving_kg__gt=0).order_by("?").first()
        or Challenge.objects.first()
    )

    # 3. Berita hangat dari GNews (Modul Community) dengan fallback anggun
    raw_news = fetch_news(limit=3)
    news_items = []
    if raw_news:
        for article in raw_news:
            time_display = (
                f"{timesince(article['published_at'])} lalu"
                if article.get("published_at")
                else "Hari ini"
            )
            news_items.append(
                {
                    "title": article.get("title", ""),
                    "source": article.get("source", "GNews"),
                    "url": article.get("url", "/community/"),
                    "time_str": time_display,
                }
            )
    else:
        news_items = FALLBACK_NEWS

    context = {
        "weekly_emissions": total_emission,
        "tip": featured_tip,
        "news": news_items,
    }
    return render(request, "home/index.html", context)
