import logging
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

GNEWS_URL = "https://gnews.io/api/v4/search"
CACHE_KEY = "community:gnews"
CACHE_SECONDS = 10 * 60
FAILED_KEY = "community:gnews:failed"
FAILED_SECONDS = 2 * 60
# Sama dengan max_length URLField di Post.news_url; Postgres menolak yang lebih panjang
URL_MAX_LENGTH = 200


def fetch_news(limit=5):
    """Berita lingkungan terbaru dari GNews. Mengembalikan [] jika gagal."""
    articles = cache.get(CACHE_KEY)
    if articles is not None:
        return articles[:limit]

    # Setelah gagal, jangan panggil API lagi sebentar agar halaman tidak menunggu timeout
    if not settings.GNEWS_API_KEY or cache.get(FAILED_KEY):
        return []

    params = {
        "q": "lingkungan OR emisi OR iklim",
        "lang": "id",
        "country": "id",
        "max": 10,
        "apikey": settings.GNEWS_API_KEY,
    }
    try:
        res = requests.get(GNEWS_URL, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
    except (requests.RequestException, ValueError):
        logger.exception("Gagal mengambil berita dari GNews")
        cache.set(FAILED_KEY, True, FAILED_SECONDS)
        return []

    # GNews kadang mengirim null, bukan string kosong, jadi pakai `or` bukan default get()
    articles = [
        {
            "title": a.get("title") or "",
            "snippet": a.get("description") or "",
            "url": a.get("url") or "",
            "source": (a.get("source") or {}).get("name") or "",
            "published_at": parse_datetime(a.get("publishedAt") or ""),
        }
        for a in data.get("articles", [])
        if a.get("title")
        and (a.get("url") or "").startswith(("http://", "https://"))
        and len(a["url"]) <= URL_MAX_LENGTH
    ]
    cache.set(CACHE_KEY, articles, CACHE_SECONDS)
    return articles[:limit]


def find_article(url):
    """Cari artikel di cache server, supaya data berita tidak bisa dipalsukan klien."""
    cached = cache.get(CACHE_KEY)
    if cached is None:
        # Cache sempat kedaluwarsa antara halaman dibuka dan tombol bagikan ditekan
        fetch_news()
        cached = cache.get(CACHE_KEY) or []
    return next((a for a in cached if a["url"] == url), None)
