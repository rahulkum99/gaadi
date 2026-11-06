import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def create_default_settings(apps, schema_editor):
    PlatformSettings = apps.get_model("fleet", "PlatformSettings")
    PlatformSettings.objects.get_or_create(singleton_key=1)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fleet", "0002_vehicle_imei"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicletelemetry",
            name="halt_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("singleton_key", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                ("daily_km_limit", models.FloatField(default=60)),
                ("long_halt_minutes", models.PositiveIntegerField(default=60)),
                ("min_stop_minutes", models.PositiveIntegerField(default=5)),
                ("stale_gps_minutes", models.PositiveIntegerField(default=15)),
                ("expire_soon_days", models.PositiveIntegerField(default=30)),
                ("expire_watch_days", models.PositiveIntegerField(default=60)),
                ("approach_ratio", models.FloatField(default=0.9)),
                ("operating_start_hour", models.PositiveSmallIntegerField(default=8)),
                ("operating_end_hour", models.PositiveSmallIntegerField(default=18)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="platform_settings_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "platform settings",
            },
        ),
        migrations.CreateModel(
            name="VehicleGpsPoint",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("captured_at", models.DateTimeField(db_index=True)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("lng", models.FloatField(blank=True, null=True)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("speed_kmh", models.FloatField(default=0)),
                ("ignition", models.BooleanField(default=False)),
                ("led_on", models.BooleanField(default=False)),
                ("gps_connected", models.BooleanField(default=False)),
                ("today_km", models.FloatField(default=0)),
                ("operating_min", models.PositiveIntegerField(default=0)),
                ("course", models.FloatField(blank=True, null=True)),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gps_points",
                        to="fleet.vehicle",
                    ),
                ),
            ],
            options={
                "ordering": ("captured_at",),
            },
        ),
        migrations.CreateModel(
            name="AlertEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("alert_type", models.CharField(max_length=32)),
                ("severity", models.CharField(max_length=16)),
                ("description", models.CharField(max_length=255)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("lat", models.FloatField(blank=True, null=True)),
                ("lng", models.FloatField(blank=True, null=True)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("today_km", models.FloatField(default=0)),
                ("speed_kmh", models.FloatField(default=0)),
                ("dedupe_key", models.CharField(max_length=160, unique=True)),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alert_events",
                        to="fleet.vehicle",
                    ),
                ),
            ],
            options={
                "ordering": ("-occurred_at",),
            },
        ),
        migrations.AddIndex(
            model_name="vehiclegpspoint",
            index=models.Index(fields=("vehicle", "captured_at"), name="fleet_vehic_vehicle_6f1c2a_idx"),
        ),
        migrations.AddIndex(
            model_name="alertevent",
            index=models.Index(fields=("vehicle", "occurred_at"), name="fleet_alert_vehicle_9a3b1c_idx"),
        ),
        migrations.AddIndex(
            model_name="alertevent",
            index=models.Index(fields=("alert_type", "occurred_at"), name="fleet_alert_alert_t_1c4d2e_idx"),
        ),
        migrations.RunPython(create_default_settings, migrations.RunPython.noop),
    ]
