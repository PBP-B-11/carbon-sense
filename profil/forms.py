from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile
from .services import city_from_token


class CityChoiceForm(forms.Form):
    city = forms.ChoiceField(
        label="Pilih kota",
        choices=[("", "Ketik di atas untuk mencari")],
        widget=forms.Select(attrs={"data-city-results": ""}),
    )

    def __init__(self, *args, cities=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].choices = [("", "Pilih kota")] + [
            (city["token"], city["label"]) for city in cities
        ]

    def clean_city(self):
        city = city_from_token(self.cleaned_data["city"])
        if not city:
            raise forms.ValidationError("Pilih kota dari hasil pencarian.")
        return city


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, cities=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"] = forms.ChoiceField(
            label="Pilih kota",
            choices=[("", "Pilih kota")]
            + [(city["token"], city["label"]) for city in cities],
            widget=forms.Select(attrs={"data-city-results": ""}),
            error_messages={
                "required": "Pilih kota dari hasil pencarian.",
                "invalid_choice": "Pilih kota dari hasil pencarian.",
            },
        )
        self.order_fields(["city"])

    def clean_city(self):
        city = city_from_token(self.cleaned_data["city"])
        if not city:
            raise forms.ValidationError("Pilih kota dari hasil pencarian.")
        return city

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            city = self.cleaned_data["city"]
            UserProfile.objects.create(
                user=user,
                city_name=city["name"],
                latitude=city["latitude"],
                longitude=city["longitude"],
            )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("bio",)
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class EmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email",)


class DeleteAccountForm(forms.Form):
    password = forms.CharField(label="Password saat ini", widget=forms.PasswordInput)
    confirm = forms.BooleanField(
        label="Saya mengerti akun dan data saya akan dihapus permanen"
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Password saat ini salah.")
        return password
