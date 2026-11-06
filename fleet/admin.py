from django.contrib import admin

from fleet.models import (
    AlertEvent,
    Constituency,
    Driver,
    PlatformSettings,
    Vehicle,
    VehicleDocument,
    VehicleGpsPoint,
    VehicleTelemetry,
)


@admin.register(Constituency)
class ConstituencyAdmin(admin.ModelAdmin):
    list_display = ("code", "number", "name", "district")
    search_fields = ("code", "name")
    list_filter = ("district",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "duty_status")
    search_fields = ("name", "phone", "licence_number")


class VehicleTelemetryInline(admin.StackedInline):
    model = VehicleTelemetry
    extra = 0


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("code", "registration", "imei", "constituency", "driver")
    search_fields = ("code", "registration", "imei")
    list_filter = ("constituency__district",)
    inlines = (VehicleTelemetryInline, VehicleDocumentInline)


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "doc_type", "approval", "end_date")
    list_filter = ("doc_type", "approval")
    search_fields = ("vehicle__code", "vehicle__registration")


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "daily_km_limit",
        "long_halt_minutes",
        "min_stop_minutes",
        "stale_gps_minutes",
        "operating_start_hour",
        "operating_end_hour",
        "updated_at",
    )


@admin.register(VehicleGpsPoint)
class VehicleGpsPointAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "captured_at", "speed_kmh", "today_km", "gps_connected")
    list_filter = ("gps_connected",)
    search_fields = ("vehicle__code", "vehicle__registration")
    date_hierarchy = "captured_at"


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "alert_type", "severity", "occurred_at", "resolved_at")
    list_filter = ("alert_type", "severity")
    search_fields = ("vehicle__code", "vehicle__registration", "description")
    date_hierarchy = "occurred_at"
