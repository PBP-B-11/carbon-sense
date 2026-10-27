from urllib.parse import urlencode

import requests
from django.core import signing
from django.core.cache import cache


def _get(url):
    for _ in range(3):
        try:
            response = requests.get(url, timeout=4)
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError:
            continue
        except (requests.RequestException, ValueError):
            break
    return None


def search_cities(query):
    if len(query) < 2:
        return []
    params = urlencode(
        {"name": query, "countryCode": "ID", "language": "id", "count": 10}
    )
    results = (
        _get(f"https://geocoding-api.open-meteo.com/v1/search?{params}") or {}
    ).get("results", [])
    return [city for city in results if city.get("country_code") == "ID"]


def city_token(city):
    return signing.dumps(
        {key: city[key] for key in ("name", "latitude", "longitude")},
        salt="profil.city",
    )


def city_from_token(token):
    try:
        city = signing.loads(token, salt="profil.city", max_age=3600)
        if (
            not city["name"]
            or not -90 <= float(city["latitude"]) <= 90
            or not -180 <= float(city["longitude"]) <= 180
        ):
            raise ValueError
        return city
    except (KeyError, TypeError, ValueError, signing.BadSignature):
        return None


def environment_snapshot(profile):
    if profile.latitude is None or profile.longitude is None:
        return None
    location = urlencode(
        {
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "timezone": "auto",
        }
    )
    weather = _get(
        "https://api.open-meteo.com/v1/forecast?"
        + location
        + "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    air_key = f"profil:air:{location}"
    air = cache.get(air_key)
    if air is None:
        air = _get(
            "https://air-quality-api.open-meteo.com/v1/air-quality?"
            + location
            + "&current=us_aqi"
        )
        if ((air or {}).get("current") or {}).get("us_aqi") is not None:
            cache.set(air_key, air, 300)
    current = {
        **((weather or {}).get("current") or {}),
        **((air or {}).get("current") or {}),
    }
    snapshot = {
        key: value
        for key, value in current.items()
        if key in ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "us_aqi")
        and value is not None
    }
    return snapshot or None
