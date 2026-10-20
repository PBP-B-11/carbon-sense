from django import forms
from .models import CarbonActivity


class CarbonActivityForm(forms.ModelForm):
    class Meta:
        model = CarbonActivity
        fields = ["activity_type", "description", "quantity", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")

        return quantity