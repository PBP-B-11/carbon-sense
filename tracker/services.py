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

# Indonesia electricity production mix Ember, 2024
ELECTRICITY_FACTOR_ID = "b51303e8-8cb4-8fce-be63-ff652cdec052"


def estimate_electricity(kwh):
    return estimate_emissions(
        ELECTRICITY_FACTOR_ID,
        {"energy": float(kwh), "energy_unit": "kWh"},
    )

#Cari faktor emisi mobil
def find_car_factors():
    response = requests.get(
        "https://api.climatiq.io/data/v1/search",
        headers={
            "Authorization": f"Bearer {settings.CLIMATIQ_API_KEY}",
        },
        params={
            "query": "passenger car",
            "unit_type": "Distance",
            "access_type": "public",
            "data_version": "^37",
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()["results"]

#Faktor mobil US EPA 2025 sebagai perkiraan berbasis data AS.
CAR_FACTOR_ID = "81caf960-fc4d-4a7b-8da2-85076a152774"


#Hitung emisi perjalanan mobil menggunakan jarak kilometer
def estimate_car_travel(km):
    return estimate_emissions(
        CAR_FACTOR_ID,
        {
            "distance": float(km),
            "distance_unit": "km",
        },
    )

#Faktor pembakaran stasioner LPG UK Government 2025, bukan emisi produksi gas.
LPG_FACTOR_ID = "62685eb5-8636-8aa1-8858-c4889af4e184"


#Kirim berat gas yang dikonsumsi dalam kg; Climatiq menangani konversi satuan.
def estimate_lpg(kg):
    return estimate_emissions(
        LPG_FACTOR_ID,
        {"weight": float(kg), "weight_unit": "kg"},
    )
