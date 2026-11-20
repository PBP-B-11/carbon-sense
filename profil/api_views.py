from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from carbon_sense.api import form_data, validate_form
from challenges.utils import ringkasan_pengguna

from .forms import (
    CityChoiceForm,
    DeleteAccountForm,
    EmailForm,
    ProfileForm,
    RegisterForm,
)
from .models import UserProfile
from .services import environment_snapshot
from .views import (
    city_options,
    claim_profile_update,
    profile_update_wait,
    save_city,
    token_city,
)


class AuthThrottle(AnonRateThrottle):
    scope = "mobile-auth"
    rate = "15/minute"

    def get_ident(self, request):
        return request.META.get("REMOTE_ADDR", "unknown")


class CitySearchThrottle(UserRateThrottle):
    scope = "mobile-city-search"
    rate = "30/minute"


def account_token(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "username": user.get_username()}


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([AuthThrottle])
def login(request):
    serializer = AuthTokenSerializer(
        data=form_data(request), context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    return Response(account_token(serializer.validated_data["user"]))


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([AuthThrottle])
@transaction.atomic
def register(request):
    data = form_data(request)
    form = RegisterForm(data, cities=token_city(data))
    validate_form(form)
    return Response(account_token(form.save()), status=201)


@api_view(["POST"])
def logout(request):
    request.auth.delete()
    return Response(status=204)


def profile_data(user, profile):
    return {
        "username": user.get_username(),
        "email": user.email,
        "bio": profile.bio,
        "city_name": profile.city_name,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "update_wait": profile_update_wait(user.pk),
    }


@api_view(["GET", "PUT", "DELETE"])
@transaction.atomic
def profile(request):
    user = request.user
    if request.method == "DELETE":
        data = form_data(request)
        if data.get("confirm") is not True:
            raise ValidationError({"confirm": ["Konfirmasi penghapusan diperlukan."]})
        validate_form(DeleteAccountForm(data, user=user))
        user.delete()
        return Response(status=204)

    record, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == "PUT":
        data = form_data(request)
        if not {"email", "bio"} <= data.keys():
            raise ValidationError("Kirim email dan bio untuk memperbarui profil.")
        email_form = EmailForm(data, instance=user)
        profile_form = ProfileForm(data, instance=record)
        errors = {**email_form.errors, **profile_form.errors}
        if errors:
            raise ValidationError(errors)
        if not claim_profile_update(user.pk):
            raise Throttled(wait=profile_update_wait(user.pk))
        email_form.save(commit=False).save(update_fields=["email"])
        profile_form.save(commit=False).save(update_fields=["bio"])
    return Response(
        {**profile_data(user, record), "challenge_stats": ringkasan_pengguna(user)}
    )


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([CitySearchThrottle])
def cities(request):
    return Response(
        {"results": city_options(request.query_params.get("q", "").strip())}
    )


@api_view(["PUT"])
def city(request):
    data = form_data(request)
    fields = validate_form(CityChoiceForm(data, cities=token_city(data)))
    record, _ = UserProfile.objects.get_or_create(user=request.user)
    save_city(record, fields["city"])
    return Response(profile_data(request.user, record))


@api_view(["GET"])
def environment(request):
    record, _ = UserProfile.objects.get_or_create(user=request.user)
    return Response(
        {"city_name": record.city_name, "snapshot": environment_snapshot(record)}
    )


@api_view(["POST"])
@transaction.atomic
def password(request):
    form = PasswordChangeForm(request.user, form_data(request))
    validate_form(form)
    form.save()
    request.auth.delete()
    return Response(status=204)
