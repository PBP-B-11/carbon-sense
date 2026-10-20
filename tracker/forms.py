from django import forms
from .models import CarbonActivity


class CarbonActivityForm(forms.ModelForm):
    activity_type = forms.ChoiceField(
        choices=[
            ("car_travel", "Mobil"),
            ("electricity", "Listrik"),
            ("meal", "Makanan"),
        ],
        widget=forms.RadioSelect(attrs={"class": "sr-only"}),
        initial="car_travel",
        label="Jenis aktivitas",
    )

    class Meta:
        model = CarbonActivity
        fields = ["activity_type", "description", "quantity", "date"]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"min": "0.01", "step": "0.01", "placeholder": "12,5"}
            ),
            "description": forms.TextInput(
                attrs={"placeholder": "Contoh: perjalanan ke kampus"}
            ),
            "date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")

        return quantity
