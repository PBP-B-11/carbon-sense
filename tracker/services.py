import requests
from django.conf import settings


def estimate_emissions(factor_id, parameters):
    if not settings.CLIMATIQ_API_KEY:
        raise ValueError("Climatiq API key is missing.")

    response = requests.post(
        "https://api.climatiq.io/data/v1/estimate",
        headers={
            "Authorization": f"Bearer {settings.CLIMATIQ_API_KEY}",
        },
        json={
            "emission_factor": {"id": factor_id},
            "parameters": parameters,
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()

def find_electricity_factors():
    response = requests.get(
        "https://api.climatiq.io/data/v1/search",
        headers={
            "Authorization": f"Bearer {settings.CLIMATIQ_API_KEY}",
        },
        params={
            "query": "electricity",
            "region": "ID",
            "unit_type": "Energy",
            "data_version": "^37",
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()["results"]