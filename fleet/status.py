from datetime import timedelta

from django.utils import timezone

from fleet.constants import (
    DAILY_KM_LIMIT,
    EXPIRE_SOON_DAYS,
    EXPIRE_WATCH_DAYS,
    LONG_HALT_MINUTES,
    STALE_GPS_MINUTES,
    ConstituencyStatus,
    DocumentValidity,
    FilterStatus,
    VehicleStatus,
)


def minutes_since(value, now=None):
    if value is None:
        return None
    now = now or timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return (now - value).total_seconds() / 60


def vehicle_status(telemetry, now=None):
    if telemetry is None or not telemetry.trip_started:
        return VehicleStatus.INACTIVE
    idle = minutes_since(telemetry.last_update, now)
    if telemetry.speed_kmh <= 2 and idle is not None and idle >= LONG_HALT_MINUTES:
        return VehicleStatus.LONG_HALT
    return VehicleStatus.ACTIVE


def is_gps_stale(telemetry, now=None):
    if telemetry is None:
        return True
    if not telemetry.gps_connected:
        return True
    idle = minutes_since(telemetry.last_update, now)
    return idle is None or idle >= STALE_GPS_MINUTES


def needs_attention(status, telemetry, now=None):
    if status == VehicleStatus.LONG_HALT:
        return True
    if is_gps_stale(telemetry, now):
        return True
    if status == VehicleStatus.ACTIVE and telemetry is not None and not telemetry.led_on:
        return True
    return False


def is_exceeded(today_km):
    return float(today_km or 0) > DAILY_KM_LIMIT


def constituency_status(vehicle_rows):
    if not vehicle_rows or all(row["status"] == VehicleStatus.INACTIVE for row in vehicle_rows):
        return ConstituencyStatus.INACTIVE
    if any(row["attention"] or row["exceeded"] for row in vehicle_rows):
        return ConstituencyStatus.NEEDS_ATTENTION
    return ConstituencyStatus.OPERATIONAL


def matches_filter(filter_status, status, attention, exceeded):
    if filter_status == FilterStatus.ACTIVE:
        return status == VehicleStatus.ACTIVE
    if filter_status == FilterStatus.LONG_HALT:
        return status == VehicleStatus.LONG_HALT
    if filter_status == FilterStatus.INACTIVE:
        return status == VehicleStatus.INACTIVE
    if filter_status == FilterStatus.ATTENTION:
        return attention
    if filter_status == FilterStatus.EXCEEDED:
        return exceeded
    return True


def document_validity(document, now=None):
    if document is None or document.end_date is None:
        return DocumentValidity.VALID
    today = (now or timezone.now()).date()
    days = (document.end_date - today).days
    if days < 0:
        return DocumentValidity.EXPIRED
    if days <= EXPIRE_SOON_DAYS:
        return DocumentValidity.EXPIRING_30
    if days <= EXPIRE_WATCH_DAYS:
        return DocumentValidity.EXPIRING_60
    return DocumentValidity.VALID


def stale_cutoff(now=None):
    return (now or timezone.now()) - timedelta(minutes=STALE_GPS_MINUTES)
