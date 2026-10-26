from django.core.management.base import BaseCommand

from challenges.models import Badge, Challenge

# Delapan lencana pada desain. Angka dan nama berasal dari data contoh Figma.
LENCANA = [
    {
        "name": "Pejalan KRL",
        "icon": "train-front",
        "tone": "amber",
        "requirement": "Selesaikan tantangan Seminggu tanpa motor.",
    },
    {
        "name": "Hijau 7 hari",
        "icon": "leaf",
        "tone": "moss",
        "requirement": "Check-in tujuh hari berturut-turut.",
    },
    {
        "name": "Hemat listrik",
        "icon": "zap",
        "tone": "teal",
        "requirement": "Selesaikan tantangan AC mati jam 22.00.",
    },
    {
        "name": "Pesepeda",
        "icon": "bike",
        "tone": "amber",
        "requirement": "Selesaikan tantangan Sepeda ke kampus.",
    },
    {
        "name": "Senin Hijau",
        "icon": "utensils",
        "tone": "moss",
        "requirement": "Selesaikan tantangan Senin tanpa daging.",
    },
    {
        "name": "Matahari Gratis",
        "icon": "sun",
        "tone": "teal",
        "requirement": "Selesaikan tantangan Jemur, bukan pengering.",
    },
    {
        "name": "Bebas Plastik",
        "icon": "sprout",
        "tone": "moss",
        "requirement": "Selesaikan tantangan Bawa botol sendiri.",
    },
    {
        "name": "Pejuang 30 hari",
        "icon": "award",
        "tone": "amber",
        "requirement": "Check-in tiga puluh hari berturut-turut.",
    },
]

TANTANGAN = [
    {
        "title": "Sepeda ke kampus",
        "category": "transportasi",
        "duration_days": 7,
        "points": 50,
        "estimated_saving_kg": "2.4",
        "icon": "bike",
        "tone": "amber",
        "badge": "Pesepeda",
        "description": "Ganti tiga perjalanan motor dengan sepeda minggu ini.",
    },
    {
        "title": "AC mati jam 22.00",
        "category": "energi",
        "duration_days": 5,
        "points": 30,
        "estimated_saving_kg": "5.7",
        "icon": "zap",
        "tone": "teal",
        "badge": "Hemat listrik",
        "description": "Matikan AC mulai pukul 22.00 selama lima malam.",
    },
    {
        "title": "Senin tanpa daging",
        "category": "makanan",
        "duration_days": 28,
        "points": 40,
        "estimated_saving_kg": "21.6",
        "icon": "utensils",
        "tone": "moss",
        "badge": "Senin Hijau",
        "description": "Makan tanpa daging merah setiap Senin selama sebulan.",
    },
    {
        "title": "Seminggu tanpa motor",
        "category": "transportasi",
        "duration_days": 7,
        "points": 50,
        "estimated_saving_kg": "6.3",
        "icon": "train-front",
        "tone": "amber",
        "badge": "Pejalan KRL",
        "description": "Pakai KRL, bus, atau jalan kaki selama tujuh hari.",
    },
    {
        "title": "Jemur, bukan pengering",
        "category": "energi",
        "duration_days": 7,
        "points": 20,
        "estimated_saving_kg": "2.7",
        "icon": "sun",
        "tone": "teal",
        "badge": "Matahari Gratis",
        "description": "Keringkan cucian di bawah matahari tiga kali.",
    },
    {
        "title": "Bawa botol sendiri",
        "category": "makanan",
        "duration_days": 5,
        "points": 30,
        "estimated_saving_kg": "0.5",
        "icon": "sprout",
        "tone": "moss",
        "badge": "Bebas Plastik",
        "description": "Tanpa air minum kemasan selama lima hari kuliah.",
    },
]


class Command(BaseCommand):
    help = "Mengisi lencana dan tantangan contoh dari desain. Aman dijalankan berulang."

    def handle(self, *args, **options):
        lencana = {}
        for data in LENCANA:
            nama = data["name"]
            obj, dibuat = Badge.objects.update_or_create(
                name=nama, defaults={k: v for k, v in data.items() if k != "name"}
            )
            lencana[nama] = obj
            self.stdout.write(f"{'+' if dibuat else '~'} lencana: {nama}")

        for data in TANTANGAN:
            isi = {k: v for k, v in data.items() if k not in ("title", "badge")}
            isi["badge"] = lencana[data["badge"]]
            obj, dibuat = Challenge.objects.update_or_create(
                title=data["title"], defaults=isi
            )
            self.stdout.write(f"{'+' if dibuat else '~'} tantangan: {obj.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai: {Badge.objects.count()} lencana, {Challenge.objects.count()} tantangan."
            )
        )
