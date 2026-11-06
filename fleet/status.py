from datetime import timedelta

from django.utils import timezone

from fleet.constants import ConstituencyStatus, DocumentValidity, FilterStatus, VehicleStatus
from fleet.platform import get_platform_settings


def minutes_since(value, now=None):
    if value is None:
        return None
    now = now or timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return (now - value).total_seconds() / 60


def halt_anchor(telemetry):
    if telemetry is None or telemetry.speed_kmh > 2:
        return None
    return telemetry.halt_started_at or telemetry.last_update


def vehicle_status(telemetry, now=None, settings=None):
    if telemetry is None or not telemetry.trip_started:
        return VehicleStatus.INACTIVE
    cfg = settings or get_platform_settings()
    halted_for = minutes_since(halt_anchor(telemetry), now)
    if telemetry.speed_kmh <= 2 and halted_for is not None and halted_for >= cfg.long_halt_minutes:
        return VehicleStatus.LONG_HALT
    return VehicleStatus.ACTIVE


def is_gps_stale(telemetry, now=None, settings=None):
    if telemetry is None:
        return True
    if not telemetry.gps_connected:
        return True
    cfg = settings or get_platform_settings()
    idle = minutes_since(telemetry.last_update, now)
    return idle is None or idle >= cfg.stale_gps_minutes


def needs_attention(status, telemetry, now=None, settings=None):
    if status == VehicleStatus.LONG_HALT:
        return True
    if is_gps_stale(telemetry, now, settings=settings):
        return True
    if status == VehicleStatus.ACTIVE and telemetry is not None and not telemetry.led_on:
        return True
    return False


def is_exceeded(today_km, settings=None):
    cfg = settings or get_platform_settings()
    return float(today_km or 0) > float(cfg.daily_km_limit)


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


def document_validity(document, now=None, settings=None):
    if document is None or document.end_date is None:
        return DocumentValidity.VALID
    cfg = settings or get_platform_settings()
    today = (now or timezone.now()).date()
    days = (document.end_date - today).days
    if days < 0:
        return DocumentValidity.EXPIRED
    if days <= cfg.expire_soon_days:
        return DocumentValidity.EXPIRING_30
    if days <= cfg.expire_watch_days:
        return DocumentValidity.EXPIRING_60
    if document.start_date:
        period = (document.end_date - document.start_date).days
        if period > 0:
            elapsed = (today - document.start_date).days
            if elapsed / period >= cfg.approach_ratio:
                return DocumentValidity.EXPIRING_30
    return DocumentValidity.VALID


def stale_cutoff(now=None, settings=None):
    cfg = settings or get_platform_settings()
    return (now or timezone.now()) - timedelta(minutes=cfg.stale_gps_minutes)
