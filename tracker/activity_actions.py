from decimal import Decimal

import requests

from .services import estimate_car_travel, estimate_electricity, estimate_meat


def process_activity_form(form, user, saving=False):
    """Return (estimate, saved_activity); attach validation/API errors to the form."""
    #Hentikan proses jika data tidak valid atau pengguna belum boleh menyimpan.
    if not form.is_valid():
        return None, None
    if saving and not user.is_authenticated:
        form.add_error(None, "Silakan login untuk menyimpan aktivitas.")
        return None, None

    #Pilih kalkulasi sesuai satuan aktivitas: kWh, km, atau gram daging.
    kind = form.cleaned_data["activity_type"]
    quantity = form.cleaned_data["quantity"]
    try:
        if kind == "electricity":
            estimate = estimate_electricity(quantity)
        elif kind == "car_travel":
            estimate = estimate_car_travel(quantity)
        elif kind in ("chicken", "beef"):
            estimate = estimate_meat(kind, quantity)
        else:
            form.add_error("activity_type", "Perhitungan untuk aktivitas ini belum tersedia.")
            return None, None
    except (requests.RequestException, ValueError):
        form.add_error(None, "Gagal menghitung emisi. Coba lagi.")
        return None, None

    #Pratinjau hanya mengembalikan estimasi tanpa menyimpan ke database.
    if not saving:
        return estimate, None

    #Simpan aktivitas baru atau hasil edit dengan pemilik dan emisi terbaru.
    activity = form.save(commit=False)
    activity.user = user
    activity.emission_kg = Decimal(str(estimate["co2e"])).quantize(Decimal("0.0001"))
    activity.save()
    return estimate, activity
