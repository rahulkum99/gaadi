from django.utils import timezone

from fleet.constants import FILTER_STATUSES, VehicleStatus
from fleet.dates import parse_query_date
from fleet.ingest import snapshot_live_fleet
from fleet.platform import get_platform_settings
from fleet.scoping import scoped_vehicles
from fleet.services import compose_vehicle, filter_vehicles
from fleet.track360 import (
    configured as track360_configured,
    devices_by_imei,
    extra_from_device,
    fetch_devices,
    normalize_imei,
    sync_vehicle_telemetry,
)


def parse_live_map_date(value):
    return parse_query_date(value)


def compose_live_map_row(vehicle, user=None, request=None, now=None, extra=None, settings=None):
    row = compose_vehicle(vehicle, user=user, request=request, now=now, settings=settings)
    extra = extra or {}
    return {
        "id": row["id"],
        "code": row["code"],
        "registration": row["registration"],
        "imei": vehicle.imei or "",
        "constituency": {
            "id": row["constituency"]["id"],
            "code": row["constituency"]["code"],
            "name": row["constituency"]["name"],
        },
        "driver": {
            "id": row["driver"]["id"],
            "name": row["driver"]["name"],
        },
        "status": row["status"],
        "attention": row["attention"],
        "exceeded": row["exceeded"],
        "today_km": row["today_km"],
        "daily_km_limit": row["daily_km_limit"],
        "speed_kmh": row["telemetry"]["speed_kmh"],
        "location": row["telemetry"]["address"],
        "lat": row["telemetry"]["lat"],
        "lng": row["telemetry"]["lng"],
        "ignition": row["telemetry"]["ignition"],
        "led_on": row["telemetry"]["led_on"],
        "gps_connected": row["telemetry"]["gps_connected"],
        "last_update": row["telemetry"]["last_update"],
        "operating_min": row["operating_min"],
        "course": extra.get("course"),
        "device_status": extra.get("device_status"),
        "vehicle_status": extra.get("vehicle_status"),
        "alarm": extra.get("alarm"),
    }


def _counts(rows):
    return {
        "total": len(rows),
        "active": sum(1 for row in rows if row["status"] == VehicleStatus.ACTIVE),
        "long_halt": sum(1 for row in rows if row["status"] == VehicleStatus.LONG_HALT),
        "inactive": sum(1 for row in rows if row["status"] == VehicleStatus.INACTIVE),
        "attention": sum(1 for row in rows if row["attention"]),
        "exceeded": sum(1 for row in rows if row["exceeded"]),
    }


def build_live_map(user, request=None, params=None, now=None):
    params = params or {}
    now = now or timezone.now()
    query_date = parse_live_map_date(params.get("date"))
    if query_date is None:
        return None, "Unknown date."
    status_filter = params.get("status") or "all"
    if status_filter not in ("all", *FILTER_STATUSES):
        return None, "Unknown status filter."
    constituency_id = params.get("constituency") or "all"
    query = params.get("q") or ""
    focused_id = (params.get("vehicle") or "").strip() or None

    live = query_date == timezone.localdate()
    cfg = get_platform_settings()
    feed = {
        "ok": True,
        "provider": "track360",
        "configured": track360_configured(),
        "live": live,
        "matched": 0,
        "unmatched": 0,
        "error": None,
    }
    extras = {}
    if live and feed["configured"]:
        devices, error = fetch_devices()
        if error:
            feed["ok"] = False
            feed["error"] = error
        else:
            stats = sync_vehicle_telemetry(devices)
            feed["matched"] = stats["matched"]
            feed["unmatched"] = stats["unmatched"]
            extras = devices_by_imei(devices)
    if live:
        snapshot_live_fleet(now=now, extras=extras)

    vehicles = scoped_vehicles(user)
    rows = [
        compose_live_map_row(
            vehicle,
            user=user,
            request=request,
            now=now,
            extra=extra_from_device(extras.get(normalize_imei(vehicle.imei))),
            settings=cfg,
        )
        for vehicle in vehicles
    ]
    if constituency_id not in ("", "all"):
        rows = [row for row in rows if row["constituency"]["id"] == str(constituency_id)]
    counts = _counts(rows)
    filtered = filter_vehicles(rows, query, "all", status_filter)
    if focused_id and not any(row["id"] == focused_id for row in filtered):
        focused_id = None
    return {
        "generated_at": now.isoformat(),
        "date": query_date.isoformat(),
        "live": live,
        "source": "track360" if live and feed["configured"] and feed["ok"] else "stored",
        "feed": feed,
        "focused_vehicle_id": focused_id,
        "thresholds": {
            "daily_km_limit": cfg.daily_km_limit,
            "long_halt_minutes": cfg.long_halt_minutes,
            "stale_gps_minutes": cfg.stale_gps_minutes,
        },
        "counts": counts,
        "vehicles": filtered,
    }, None
