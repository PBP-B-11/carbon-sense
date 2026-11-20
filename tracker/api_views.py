from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from carbon_sense.api import form_data, paginate

from .activity_actions import process_activity_form
from .dashboard import build_dashboard_context
from .forms import CarbonActivityForm
from .models import CarbonActivity


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarbonActivity
        fields = (
            "id",
            "activity_type",
            "description",
            "quantity",
            "emission_kg",
            "date",
        )


class EstimateThrottle(UserRateThrottle):
    rate = "20/minute"
    scope = "mobile-emission-estimate"


def user_activities(user):
    return CarbonActivity.objects.filter(user=user).order_by("-date", "-pk")


def process_activity(request, *, activity=None, saving=False):
    form = CarbonActivityForm(form_data(request), instance=activity)
    estimate, saved = process_activity_form(form, request.user, saving=saving)
    if form.errors:
        return Response(form.errors, status=400)
    if not saving:
        return Response({"estimate": estimate})
    return Response(ActivitySerializer(saved).data, status=200 if activity else 201)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EstimateThrottle])
def estimate(request):
    return process_activity(request)


@api_view(["GET"])
def dashboard(request):
    return Response(
        build_dashboard_context(
            user_activities(request.user),
            request.query_params.get("period", "week"),
            timezone.localdate(),
        )
    )


@api_view(["GET", "POST"])
def activities(request):
    if request.method == "POST":
        return process_activity(request, saving=True)
    return paginate(request, user_activities(request.user), ActivitySerializer, 20)


@api_view(["GET", "PUT", "DELETE"])
def activity_detail(request, pk):
    activity = get_object_or_404(user_activities(request.user), pk=pk)
    if request.method == "DELETE":
        activity.delete()
        return Response(status=204)
    if request.method == "PUT":
        return process_activity(request, activity=activity, saving=True)
    return Response(ActivitySerializer(activity).data)
