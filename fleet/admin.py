from django.contrib import admin

from fleet.models import Constituency, Driver, Vehicle, VehicleDocument, VehicleTelemetry


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
    list_display = ("code", "registration", "constituency", "driver")
    search_fields = ("code", "registration")
    list_filter = ("constituency__district",)
    inlines = (VehicleTelemetryInline, VehicleDocumentInline)


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "doc_type", "approval", "end_date")
    list_filter = ("doc_type", "approval")
    search_fields = ("vehicle__code", "vehicle__registration")
