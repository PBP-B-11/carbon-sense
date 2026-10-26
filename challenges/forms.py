from django import forms

from .models import Challenge

# Simbol ikon yang tersedia di sprite base.html
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
