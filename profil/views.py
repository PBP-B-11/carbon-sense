from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST

from .forms import CityChoiceForm, DeleteAccountForm, EmailForm, ProfileForm, RegisterForm
from .models import UserProfile
from .services import city_from_token, city_token, environment_snapshot, search_cities


def city_options(query):
    return [
        {'token': city_token(city), 'label': ', '.join(filter(None, (city['name'], city.get('admin1'))))}
        for city in search_cities(query) if city.get('name') and city.get('latitude') is not None and city.get('longitude') is not None
    ]


@require_GET
def city_search(request):
    return JsonResponse({'results': city_options(request.GET.get('q', '').strip())})


def token_city(request):
    city = city_from_token(request.POST.get('city', ''))
    return [{'token': request.POST.get('city', ''), 'label': city['name']}] if city else []


def register(request):
    options = token_city(request) if request.method == 'POST' else ()
    form = RegisterForm(request.POST or None, cities=options)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('profil:index')
    return render(request, 'profil/register.html', {
        'form': form,
        'city_search': request.POST.get('city_search', ''),
    })


class SignInView(LoginView):
    template_name = 'profil/login.html'


class ChangePasswordView(PasswordChangeView):
    template_name = 'profil/password.html'
    success_url = reverse_lazy('profil:index')


@login_required
def index(request, email_form=None, profile_form=None, city_form=None):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'profil/profil.html', {
        'profile': profile,
        'snapshot': environment_snapshot(profile),
        'email_form': email_form if email_form is not None else EmailForm(instance=request.user),
        'profile_form': profile_form if profile_form is not None else ProfileForm(instance=profile),
        'city_form': city_form if city_form is not None else CityChoiceForm(),
    })


@login_required
@require_POST
def update_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    email_form = EmailForm(request.POST, instance=request.user)
    profile_form = ProfileForm(request.POST, instance=profile)
    if email_form.is_valid() and profile_form.is_valid():
        email_form.save()
        profile_form.save()
        return redirect('profil:index')
    return index(request, email_form=email_form, profile_form=profile_form)


@login_required
@require_POST
def update_city(request):
    form = CityChoiceForm(request.POST, cities=token_city(request))
    if form.is_valid():
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        city = form.cleaned_data['city']
        profile.city_name = city['name']
        profile.latitude = city['latitude']
        profile.longitude = city['longitude']
        profile.save()
        return redirect('profil:index')
    return index(request, city_form=form)


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        request.user.delete()
        logout(request)
        return redirect('home:index')
    return render(request, 'profil/delete.html', {'form': form})


@require_POST
def sign_out(request):
    logout(request)
    return redirect('home:index')
