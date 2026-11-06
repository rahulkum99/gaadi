from django.core.management.base import BaseCommand

from fleet.ingest import ingest_live_fleet


class Command(BaseCommand):
    help = "Pull Track360 GPS, save a 5-minute snapshot, and raise alerts from platform settings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Save a snapshot even if one was stored less than 5 minutes ago.",
        )

    def handle(self, *args, **options):
        result = ingest_live_fleet(force=options["force"])
        feed = result["feed"]
        snapshot = result["snapshot"]
        if feed["error"]:
            self.stdout.write(self.style.WARNING(f"Track360: {feed['error']}"))
        self.stdout.write(
            self.style.SUCCESS(
                "Live ingest matched={matched} unmatched={unmatched} points={points} alerts={alerts} skipped={skipped}".format(
                    matched=feed["matched"],
                    unmatched=feed["unmatched"],
                    points=snapshot["points"],
                    alerts=snapshot["alerts"],
                    skipped=snapshot["skipped"],
                )
            )
        )
