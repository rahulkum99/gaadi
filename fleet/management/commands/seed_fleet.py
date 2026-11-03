from django.core.management.base import BaseCommand

from fleet.seed import seed_demo_fleet, seed_goa_constituencies


class Command(BaseCommand):
    help = "Seed 40 Goa constituencies and a small demo fleet."

    def handle(self, *args, **options):
        constituencies = seed_goa_constituencies()
        vehicles = seed_demo_fleet()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {constituencies} new constituencies and {vehicles} new demo vehicles."
            )
        )
