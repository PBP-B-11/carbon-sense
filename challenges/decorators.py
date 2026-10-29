from functools import wraps

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


def require_superuser_json(view_func):
    """Decorator untuk memastikan pengguna yang mengakses endpoint JSON adalah superuser."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)
        if not request.user.is_superuser:
            return JsonResponse(
                {"error": "Akses ditolak: Hanya superuser yang memiliki izin."},
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def require_superuser_html(view_func):
    """Decorator untuk memastikan pengguna yang mengakses halaman HTML adalah superuser."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise PermissionDenied("Hanya superuser yang dapat mengakses halaman ini.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def ratelimit_endpoint(max_requests=20, window_seconds=60):
    """Decorator rate limiting berbasis cache Django untuk membatasi frekuensi request.

    Mencegah brute force dan automated spamming pada endpoint sensitif.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            identitas = (
                f"user_{request.user.id}"
                if request.user.is_authenticated
                else f"ip_{request.META.get('REMOTE_ADDR', 'unknown')}"
            )
            cache_key = f"ratelimit:{view_func.__name__}:{identitas}"
            request_count = cache.get(cache_key, 0)

            if request_count >= max_requests:
                return JsonResponse(
                    {
                        "error": "Terlalu banyak permintaan. Silakan tunggu beberapa saat.",
                        "status": "rate_limited",
                        "retry_after_seconds": window_seconds,
                    },
                    status=429,
                )

            if request_count == 0:
                cache.set(cache_key, 1, window_seconds)
            else:
                try:
                    cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, 1, window_seconds)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
