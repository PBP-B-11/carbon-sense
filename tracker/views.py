from django.shortcuts import render
from .forms import CarbonActivityForm


def index(request):
    form = CarbonActivityForm()
    return render(request, "tracker/tracker.html", {"form": form})