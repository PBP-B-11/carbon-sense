from django.conf import settings
from django.db import models
from django.utils import timezone


class CarbonActivity(models.Model):
    ACTIVITY_CHOICES = [
        ("car_travel", "Car travel (km)"),
        ("electricity", "Electricity (kWh)"),
        #Kuantitas LPG adalah berat gas yang dikonsumsi dalam kilogram.
        ("lpg", "Cooking gas LPG (kg)"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_CHOICES,
    )
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    emission_kg = models.DecimalField(max_digits=12, decimal_places=4)
    date = models.DateField(default=timezone.localdate)
