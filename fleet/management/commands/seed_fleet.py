from django.core.management.base import BaseCommand

from fleet.models import Constituency
from fleet.seed import seed_demo_fleet


class Command(BaseCommand):
    help = (
        "Seed a small demo fleet onto constituencies Super Admin has already created. "
        "Does not create constituencies."
    )

    def handle(self, *args, **options):
        if not Constituency.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No constituencies found. Super Admin must add them first with "
                    "POST /api/v1/constituencies/ (name, district, optional number, lat, lng, image)."
                )
            )
            return
        vehicles = seed_demo_fleet()
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {vehicles} new demo vehicles onto existing constituencies.")
        )
