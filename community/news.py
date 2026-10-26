import logging
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

GNEWS_URL = "https://gnews.io/api/v4/search"
CACHE_KEY = "community:gnews"
CACHE_SECONDS = 10 * 60


def fetch_news(limit=3):
    """Berita lingkungan terbaru dari GNews. Mengembalikan [] jika gagal."""
    articles = cache.get(CACHE_KEY)
    if articles is not None:
        return articles[:limit]

    if not settings.GNEWS_API_KEY:
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
    except requests.RequestException:
        logger.exception("Gagal mengambil berita dari GNews")
        return []

    articles = [
        {
            "title": a.get("title", ""),
            "snippet": a.get("description", ""),
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": parse_datetime(a.get("publishedAt", "")),
        }
        for a in data.get("articles", [])
        if a.get("title") and a.get("url")
    ]
    cache.set(CACHE_KEY, articles, CACHE_SECONDS)
    return articles[:limit]


def find_article(url):
    """Cari artikel di cache server, supaya data berita tidak bisa dipalsukan klien."""
    cached = cache.get(CACHE_KEY) or []
    return next((a for a in cached if a["url"] == url), None)
