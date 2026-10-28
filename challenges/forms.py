from django import forms

from .models import Challenge

IKON_PILIHAN = [
    ("bike", "Sepeda"),
    ("train-front", "Kereta"),
    ("car", "Mobil"),
    ("zap", "Listrik"),
    ("sun", "Matahari"),
    ("wind", "Angin"),
    ("droplets", "Air"),
    ("utensils", "Makanan"),
    ("leaf", "Daun"),
    ("sprout", "Tunas"),
    ("star", "Bintang"),
    ("award", "Penghargaan"),
]


class TantanganForm(forms.ModelForm):
    icon = forms.ChoiceField(label="Ikon", choices=IKON_PILIHAN)

    class Meta:
        model = Challenge
        fields = [
            "title",
            "description",
            "category",
            "duration_days",
            "points",
            "estimated_saving_kg",
            "badge",
            "icon",
            "tone",
        ]
        labels = {
            "title": "Judul tantangan",
            "description": "Deskripsi",
            "category": "Kategori",
            "duration_days": "Durasi (hari)",
            "points": "Hadiah poin",
            "estimated_saving_kg": "Perkiraan hemat (kg CO₂e)",
            "badge": "Lencana hadiah",
            "tone": "Warna ikon",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_duration_days(self):
        durasi = self.cleaned_data["duration_days"]
        if durasi < 1:
            raise forms.ValidationError("Durasi minimal 1 hari.")
        return durasi

    def clean_points(self):
        points = self.cleaned_data.get("points")
        category = self.cleaned_data.get("category")
        if (
            category == Challenge.Category.TRANSPORT
            and points is not None
            and points < 10
        ):
            raise forms.ValidationError(
                "Tantangan transportasi harus memiliki minimal 10 poin."
            )
        return points

    def clean_estimated_saving_kg(self):
        estimated_saving_kg = self.cleaned_data.get("estimated_saving_kg")
        if estimated_saving_kg is not None and estimated_saving_kg < 0:
            raise forms.ValidationError("Perkiraan hemat tidak boleh negatif.")
        return estimated_saving_kg

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title:
            qs = Challenge.objects.filter(title__iexact=title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Judul tantangan sudah ada.")
        return title
