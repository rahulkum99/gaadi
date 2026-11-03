from django.conf import settings
from django.db import models

from base.models import TimeStampedUUIDModel
from fleet.constants import (
    APPROVAL_STATUSES,
    DISTRICTS,
    DOCUMENT_TYPES,
    DUTY_STATUSES,
    DutyStatus,
    constituency_code,
)


def constituency_image_path(instance, filename):
    return f"constituencies/{instance.id}/{filename}"


def driver_photo_path(instance, filename):
    return f"drivers/{instance.id}/{filename}"


def vehicle_photo_path(instance, filename):
    return f"vehicles/{instance.id}/photo/{filename}"


def vehicle_plate_path(instance, filename):
    return f"vehicles/{instance.id}/plate/{filename}"


def vehicle_led_path(instance, filename):
    return f"vehicles/{instance.id}/led/{filename}"


def vehicle_chassis_path(instance, filename):
    return f"vehicles/{instance.id}/chassis/{filename}"


def vehicle_document_path(instance, filename):
    return f"vehicles/{instance.vehicle_id}/documents/{instance.doc_type}/{filename}"


class Constituency(TimeStampedUUIDModel):
    number = models.PositiveIntegerField(unique=True)
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    district = models.CharField(max_length=32, choices=[(item, item) for item in DISTRICTS])
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    image = models.ImageField(upload_to=constituency_image_path, blank=True, null=True)

    class Meta:
        ordering = ("number",)

    def __str__(self):
        return f"{self.code} {self.name}"

    def save(self, *args, **kwargs):
        if self.number and not self.code:
            self.code = constituency_code(self.number)
        super().save(*args, **kwargs)

    @property
    def district_label(self):
        from fleet.constants import DISTRICT_LABELS

        return DISTRICT_LABELS.get(self.district, self.district)


class Driver(TimeStampedUUIDModel):
    name = models.CharField(max_length=128)
    phone = models.CharField(max_length=32, blank=True)
    photo = models.ImageField(upload_to=driver_photo_path, blank=True, null=True)
    licence_number = models.CharField(max_length=64, blank=True)
    licence_expiry = models.DateField(null=True, blank=True)
    duty_status = models.CharField(
        max_length=16,
        choices=[(item, item) for item in DUTY_STATUSES],
        default=DutyStatus.OFF_DUTY,
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Vehicle(TimeStampedUUIDModel):
    code = models.CharField(max_length=32, unique=True)
    registration = models.CharField(max_length=32, unique=True)
    constituency = models.ForeignKey(
        Constituency,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="vehicles",
    )
    photo = models.ImageField(upload_to=vehicle_photo_path, blank=True, null=True)
    plate_photo = models.ImageField(upload_to=vehicle_plate_path, blank=True, null=True)
    led_photo = models.ImageField(upload_to=vehicle_led_path, blank=True, null=True)
    chassis_photo = models.ImageField(upload_to=vehicle_chassis_path, blank=True, null=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return self.code


class VehicleTelemetry(TimeStampedUUIDModel):
    vehicle = models.OneToOneField(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="telemetry",
    )
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    speed_kmh = models.FloatField(default=0)
    ignition = models.BooleanField(default=False)
    led_on = models.BooleanField(default=False)
    gps_connected = models.BooleanField(default=False)
    last_update = models.DateTimeField(null=True, blank=True)
    trip_started = models.BooleanField(default=False)
    today_km = models.FloatField(default=0)
    operating_min = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "vehicle telemetry"

    def __str__(self):
        return f"telemetry:{self.vehicle.code}"


class VehicleDocument(TimeStampedUUIDModel):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=32, choices=[(item, item) for item in DOCUMENT_TYPES])
    file = models.FileField(upload_to=vehicle_document_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    approval = models.CharField(
        max_length=16,
        choices=[(item, item) for item in APPROVAL_STATUSES],
        blank=True,
        null=True,
    )
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_documents",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("vehicle", "doc_type"),
                name="unique_vehicle_document_type",
            ),
        ]
        ordering = ("vehicle_id", "doc_type")

    def __str__(self):
        return f"{self.vehicle.code}:{self.doc_type}"
