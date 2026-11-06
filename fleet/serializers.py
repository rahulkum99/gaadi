from rest_framework import serializers

from fleet.constants import (
    APPROVAL_STATUSES,
    DISTRICTS,
    DOCUMENT_TYPES,
    DUTY_STATUSES,
    PLATFORM_DEFAULTS,
    ApprovalStatus,
    DutyStatus,
    constituency_code,
    format_vehicle_code,
)
from fleet.models import Constituency, Driver, PlatformSettings, Vehicle, VehicleTelemetry
from fleet.services import ensure_vehicle_documents, next_constituency_number, next_vehicle_serial


class ConstituencyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Constituency
        fields = ("name", "district", "number", "lat", "lng", "image")
        extra_kwargs = {
            "number": {"required": False},
            "lat": {"required": False},
            "lng": {"required": False},
            "image": {"required": False},
        }

    def validate_district(self, value):
        if value not in DISTRICTS:
            raise serializers.ValidationError("Unknown district.")
        return value

    def create(self, validated_data):
        number = validated_data.get("number") or next_constituency_number()
        validated_data["number"] = number
        validated_data["code"] = constituency_code(number)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "number" in validated_data:
            validated_data["code"] = constituency_code(validated_data["number"])
        return super().update(instance, validated_data)


class DriverWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ("name", "phone", "photo", "licence_number", "licence_expiry", "duty_status")
        extra_kwargs = {
            "phone": {"required": False},
            "photo": {"required": False},
            "licence_number": {"required": False},
            "licence_expiry": {"required": False},
            "duty_status": {"required": False},
        }

    def validate_duty_status(self, value):
        if value not in DUTY_STATUSES:
            raise serializers.ValidationError("Unknown duty status.")
        return value


class TelemetryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleTelemetry
        fields = (
            "lat",
            "lng",
            "address",
            "speed_kmh",
            "ignition",
            "led_on",
            "gps_connected",
            "last_update",
            "trip_started",
            "today_km",
            "operating_min",
            "halt_started_at",
        )


class VehicleCreateSerializer(serializers.Serializer):
    constituency = serializers.UUIDField()
    registration = serializers.CharField(max_length=32)
    imei = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    driver_name = serializers.CharField(max_length=128)
    driver_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    driver_licence_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    driver_licence_expiry = serializers.DateField(required=False, allow_null=True)
    driver_duty_status = serializers.CharField(required=False)
    photo = serializers.ImageField(required=False)
    plate_photo = serializers.ImageField(required=False)
    led_photo = serializers.ImageField(required=False)
    chassis_photo = serializers.ImageField(required=False)

    def validate_constituency(self, value):
        constituency = Constituency.objects.filter(pk=value).first()
        if constituency is None:
            raise serializers.ValidationError("Unknown constituency.")
        return constituency

    def validate_registration(self, value):
        value = value.strip().upper()
        if Vehicle.objects.filter(registration=value).exists():
            raise serializers.ValidationError("Registration already exists.")
        return value

    def validate_imei(self, value):
        value = (value or "").strip()
        if not value:
            return None
        if Vehicle.objects.filter(imei=value).exists():
            raise serializers.ValidationError("IMEI already exists.")
        return value

    def validate_driver_duty_status(self, value):
        if value and value not in DUTY_STATUSES:
            raise serializers.ValidationError("Unknown duty status.")
        return value or DutyStatus.OFF_DUTY

    def create(self, validated_data):
        constituency = validated_data.pop("constituency")
        driver = Driver.objects.create(
            name=validated_data.pop("driver_name"),
            phone=validated_data.pop("driver_phone", ""),
            licence_number=validated_data.pop("driver_licence_number", ""),
            licence_expiry=validated_data.pop("driver_licence_expiry", None),
            duty_status=validated_data.pop("driver_duty_status", DutyStatus.OFF_DUTY),
        )
        serial = next_vehicle_serial(constituency)
        vehicle = Vehicle.objects.create(
            code=format_vehicle_code(constituency.district, constituency.number, serial),
            registration=validated_data["registration"],
            imei=validated_data.get("imei"),
            constituency=constituency,
            driver=driver,
            photo=validated_data.get("photo"),
            plate_photo=validated_data.get("plate_photo"),
            led_photo=validated_data.get("led_photo"),
            chassis_photo=validated_data.get("chassis_photo"),
        )
        VehicleTelemetry.objects.create(vehicle=vehicle)
        ensure_vehicle_documents(vehicle)
        return vehicle


class VehicleUpdateSerializer(serializers.Serializer):
    constituency = serializers.UUIDField(required=False)
    registration = serializers.CharField(max_length=32, required=False)
    imei = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    driver_name = serializers.CharField(max_length=128, required=False)
    driver_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    driver_licence_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    driver_licence_expiry = serializers.DateField(required=False, allow_null=True)
    driver_duty_status = serializers.CharField(required=False)
    photo = serializers.ImageField(required=False)
    plate_photo = serializers.ImageField(required=False)
    led_photo = serializers.ImageField(required=False)
    chassis_photo = serializers.ImageField(required=False)
    telemetry = TelemetryWriteSerializer(required=False)

    def validate_constituency(self, value):
        constituency = Constituency.objects.filter(pk=value).first()
        if constituency is None:
            raise serializers.ValidationError("Unknown constituency.")
        return constituency

    def validate_registration(self, value):
        value = value.strip().upper()
        queryset = Vehicle.objects.filter(registration=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Registration already exists.")
        return value

    def validate_imei(self, value):
        value = (value or "").strip()
        if not value:
            return None
        queryset = Vehicle.objects.filter(imei=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("IMEI already exists.")
        return value

    def validate_driver_duty_status(self, value):
        if value and value not in DUTY_STATUSES:
            raise serializers.ValidationError("Unknown duty status.")
        return value

    def update(self, instance, validated_data):
        telemetry_data = validated_data.pop("telemetry", None)
        constituency = validated_data.pop("constituency", None)
        if constituency is not None:
            instance.constituency = constituency
        if "registration" in validated_data:
            instance.registration = validated_data["registration"]
        if "imei" in validated_data:
            instance.imei = validated_data["imei"]
        for field in ("photo", "plate_photo", "led_photo", "chassis_photo"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        driver = instance.driver
        mapping = {
            "driver_name": "name",
            "driver_phone": "phone",
            "driver_licence_number": "licence_number",
            "driver_licence_expiry": "licence_expiry",
            "driver_duty_status": "duty_status",
        }
        driver_updated = False
        for source, target in mapping.items():
            if source in validated_data:
                setattr(driver, target, validated_data[source])
                driver_updated = True
        if driver_updated:
            driver.save()

        if telemetry_data is not None:
            telemetry, _ = VehicleTelemetry.objects.get_or_create(vehicle=instance)
            for field, value in telemetry_data.items():
                setattr(telemetry, field, value)
            telemetry.save()
        return instance


class DocumentUpsertSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    file_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def update(self, instance, validated_data):
        if "file" in validated_data:
            instance.file = validated_data["file"]
            instance.file_name = (
                validated_data.get("file_name")
                or getattr(validated_data["file"], "name", instance.file_name)
            )
        elif validated_data.get("file_name"):
            instance.file_name = validated_data["file_name"]
        if "start_date" in validated_data:
            instance.start_date = validated_data["start_date"]
        if "end_date" in validated_data:
            instance.end_date = validated_data["end_date"]
        instance.approval = ApprovalStatus.PENDING
        instance.review_comment = ""
        instance.reviewed_at = None
        instance.reviewed_by = None
        instance.save()
        return instance


class DocumentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=APPROVAL_STATUSES)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate_decision(self, value):
        if value not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise serializers.ValidationError("Decision must be approved or rejected.")
        return value


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = (
            "daily_km_limit",
            "long_halt_minutes",
            "min_stop_minutes",
            "stale_gps_minutes",
            "expire_soon_days",
            "expire_watch_days",
            "approach_ratio",
            "operating_start_hour",
            "operating_end_hour",
        )

    def validate_daily_km_limit(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Daily km limit must be greater than 0.")
        return value

    def validate_long_halt_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError("Long halt threshold must be at least 1 minute.")
        return value

    def validate_min_stop_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError("Minimum stop duration must be at least 1 minute.")
        return value

    def validate_stale_gps_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError("Stale GPS threshold must be at least 1 minute.")
        return value

    def validate_expire_soon_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Expiring soon must be at least 1 day.")
        return value

    def validate_expire_watch_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Expiring watch must be at least 1 day.")
        return value

    def validate_approach_ratio(self, value):
        if value is None or value < 0 or value > 1:
            raise serializers.ValidationError("Approach ratio must be between 0 and 1.")
        return value

    def validate_operating_start_hour(self, value):
        if value < 0 or value > 23:
            raise serializers.ValidationError("Start hour must be between 0 and 23.")
        return value

    def validate_operating_end_hour(self, value):
        if value < 0 or value > 23:
            raise serializers.ValidationError("End hour must be between 0 and 23.")
        return value

    def validate(self, attrs):
        def current(name):
            if name in attrs:
                return attrs[name]
            if self.instance is not None:
                return getattr(self.instance, name)
            return PLATFORM_DEFAULTS[name]

        if current("long_halt_minutes") < current("min_stop_minutes"):
            raise serializers.ValidationError(
                {"long_halt_minutes": "Must be greater than or equal to the minimum stop duration."}
            )
        if current("expire_watch_days") <= current("expire_soon_days"):
            raise serializers.ValidationError(
                {"expire_watch_days": "Must be greater than expiring soon, used for the wider watch window."}
            )
        if current("operating_end_hour") <= current("operating_start_hour"):
            raise serializers.ValidationError(
                {"operating_end_hour": "End of the operating day must be after the start hour."}
            )
        return attrs

