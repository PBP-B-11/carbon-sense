from django.contrib import admin
from .models import CarbonActivity


@admin.register(CarbonActivity)
class CarbonActivityAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "activity_type",
        "quantity",
        "emission_kg",
        "date",
    )