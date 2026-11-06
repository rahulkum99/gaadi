import logging

from django.db.models import Max
from django.utils import timezone

from fleet.alerts import evaluate_vehicle_alerts
from fleet.constants import LIVE_SNAPSHOT_MINUTES
from fleet.models import Vehicle, VehicleGpsPoint, VehicleTelemetry
from fleet.platform import get_platform_settings
from fleet.track360 import (
    configured as track360_configured,
    extra_from_device,
    fetch_devices,
    normalize_imei,
    sync_vehicle_telemetry,
)

logger = logging.getLogger("fleet")


def update_motion_state(telemetry, now, settings, last_captured_at=None):
    local_day = timezone.localdate(now)
    if last_captured_at is not None and timezone.localdate(last_captured_at) != local_day:
        telemetry.operating_min = 0
    if not telemetry.trip_started or telemetry.speed_kmh > 2:
        telemetry.halt_started_at = None
    elif telemetry.halt_started_at is None:
        telemetry.halt_started_at = telemetry.last_update or now
    hour = timezone.localtime(now).hour
    on_duty = settings.operating_start_hour <= hour < settings.operating_end_hour
    if on_duty and telemetry.trip_started and (telemetry.ignition or telemetry.speed_kmh > 2):
        telemetry.operating_min += LIVE_SNAPSHOT_MINUTES


def save_gps_point(vehicle, telemetry, now, extra=None):
    extra = extra or {}
    return VehicleGpsPoint.objects.create(
        vehicle=vehicle,
        captured_at=now,
        lat=telemetry.lat,
        lng=telemetry.lng,
        address=telemetry.address or "",
        speed_kmh=telemetry.speed_kmh or 0,
        ignition=telemetry.ignition,
        led_on=telemetry.led_on,
        gps_connected=telemetry.gps_connected,
        today_km=telemetry.today_km or 0,
        operating_min=telemetry.operating_min or 0,
        course=extra.get("course"),
    )


def snapshot_live_fleet(now=None, force=False, extras=None):
    now = now or timezone.now()
    cfg = get_platform_settings()
    extras = extras or {}
    last_times = dict(
        VehicleGpsPoint.objects.values("vehicle_id").annotate(ts=Max("captured_at")).values_list("vehicle_id", "ts")
    )
    vehicles = Vehicle.objects.select_related("telemetry")
    created_points = 0
    created_alerts = 0
    skipped = 0
    for vehicle in vehicles:
        telemetry = getattr(vehicle, "telemetry", None)
        if telemetry is None:
            continue
        last_captured = last_times.get(vehicle.id)
        if not force and last_captured is not None:
            elapsed = (now - last_captured).total_seconds() / 60
            if elapsed < LIVE_SNAPSHOT_MINUTES:
                skipped += 1
                created_alerts += evaluate_vehicle_alerts(vehicle, telemetry, settings=cfg, now=now)
                continue
        update_motion_state(telemetry, now, cfg, last_captured_at=last_captured)
        telemetry.save(
            update_fields=["operating_min", "halt_started_at", "updated_at"]
        )
        extra = extras.get(normalize_imei(vehicle.imei)) if vehicle.imei else None
        save_gps_point(vehicle, telemetry, now, extra=extra_from_device(extra) if extra else None)
        created_points += 1
        created_alerts += evaluate_vehicle_alerts(vehicle, telemetry, settings=cfg, now=now)
    logger.info(
        "live_snapshot points=%s alerts=%s skipped=%s",
        created_points,
        created_alerts,
        skipped,
    )
    return {
        "points": created_points,
        "alerts": created_alerts,
        "skipped": skipped,
        "interval_minutes": LIVE_SNAPSHOT_MINUTES,
    }


def ingest_live_fleet(now=None, force=False):
    now = now or timezone.now()
    feed = {
        "ok": True,
        "provider": "track360",
        "configured": track360_configured(),
        "matched": 0,
        "unmatched": 0,
        "error": None,
    }
    extras = {}
    if feed["configured"]:
        devices, error = fetch_devices()
        if error:
            feed["ok"] = False
            feed["error"] = error
        else:
            stats = sync_vehicle_telemetry(devices)
            feed["matched"] = stats["matched"]
            feed["unmatched"] = stats["unmatched"]
            extras = {
                normalize_imei(item.get("deviceImei") or item.get("imei")): item
                for item in devices
                if normalize_imei(item.get("deviceImei") or item.get("imei"))
            }
    snapshot = snapshot_live_fleet(now=now, force=force, extras=extras)
    return {"feed": feed, "snapshot": snapshot}
