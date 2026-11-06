import json
import logging
from datetime import datetime, timezone as dt_timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from fleet.models import Vehicle, VehicleTelemetry

logger = logging.getLogger("fleet")

CACHE_KEY = "fleet:track360:devices"


def normalize_imei(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def coerce_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value, default=None):
    number = coerce_float(value, default=None)
    if number is None:
        return default
    return int(number)


def clean_alarm(value):
    if value in (None, "", "null", "None"):
        return None
    return str(value)


def parse_track360_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if len(text) >= 5 and text[-5] in {"+", "-"} and text[-3] != ":":
        text = f"{text[:-2]}:{text[-2:]}"
    text = text.replace(" ", "T", 1)
    parsed = parse_datetime(text)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def meters_to_km(value):
    meters = coerce_float(value, 0) or 0
    return round(meters / 1000.0, 1)


def configured():
    return bool(getattr(settings, "TRACK360_USERNAME", "") and getattr(settings, "TRACK360_PASSWORD", ""))


def _request_devices():
    query = urlencode(
        {
            "username": settings.TRACK360_USERNAME,
            "password": settings.TRACK360_PASSWORD,
        }
    )
    url = f"{settings.TRACK360_PULL_URL}?{query}"
    request = Request(url, headers={"Accept": "application/json"})
    timeout = getattr(settings, "TRACK360_TIMEOUT_SECONDS", 15)
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if str(payload.get("status", "")).lower() != "success":
        message = payload.get("message") or "Track360 pull failed."
        raise RuntimeError(message)
    data = payload.get("data") or []
    if isinstance(data, dict):
        return [data]
    return list(data)


def fetch_devices():
    if not configured():
        return [], None
    cache_seconds = getattr(settings, "TRACK360_CACHE_SECONDS", 20)
    if cache_seconds:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached, None
    try:
        devices = _request_devices()
    except HTTPError as exc:
        logger.warning("track360_pull_failed http_status=%s", exc.code)
        return [], f"Track360 HTTP {exc.code}"
    except (URLError, TimeoutError) as exc:
        logger.warning("track360_pull_failed error=%s", type(exc).__name__)
        return [], "Track360 network error"
    except (ValueError, RuntimeError) as exc:
        logger.warning("track360_pull_failed error=%s", type(exc).__name__)
        return [], str(exc)
    if cache_seconds:
        cache.set(CACHE_KEY, devices, cache_seconds)
    logger.info("track360_pull_ok devices=%s", len(devices))
    return devices, None


def devices_by_imei(devices):
    mapped = {}
    for device in devices:
        imei = normalize_imei(device.get("deviceImei") or device.get("imei"))
        if imei:
            mapped[imei] = device
    return mapped


def extra_from_device(device):
    if not device:
        return {}
    course = coerce_float(device.get("course"))
    return {
        "course": course,
        "device_status": device.get("status") or None,
        "vehicle_status": device.get("vehicle_status") or None,
        "alarm": clean_alarm(device.get("alarm")),
        "device_id": device.get("deviceId"),
        "pos_id": device.get("posId"),
    }


def map_device_to_telemetry(device):
    lat = coerce_float(device.get("latitude"))
    lng = coerce_float(device.get("longitude"))
    speed = coerce_float(device.get("speed"), 0) or 0
    ignition = coerce_bool(device.get("ignition"))
    today_km = meters_to_km(device.get("daily_distance"))
    status = str(device.get("status") or "").strip().lower()
    valid = device.get("valid")
    gps_connected = status == "online" and valid not in {0, "0", False, "false"}
    last_update = (
        parse_track360_datetime(device.get("lastUpdate"))
        or parse_track360_datetime(device.get("deviceTime"))
        or parse_track360_datetime(device.get("deviceFixTime"))
    )
    trip_started = today_km > 0.05 or ignition or speed > 2
    payload = {
        "speed_kmh": speed,
        "ignition": ignition,
        "gps_connected": gps_connected,
        "last_update": last_update,
        "trip_started": trip_started,
        "today_km": today_km,
    }
    if lat is not None and lng is not None:
        payload["lat"] = lat
        payload["lng"] = lng
    return payload


def sync_vehicle_telemetry(devices):
    by_imei = devices_by_imei(devices)
    if not by_imei:
        return {"matched": 0, "unmatched": 0, "updated": 0}
    vehicles = list(
        Vehicle.objects.filter(imei__in=by_imei.keys()).select_related("telemetry")
    )
    updated = 0
    for vehicle in vehicles:
        fields = map_device_to_telemetry(by_imei[vehicle.imei])
        telemetry, _ = VehicleTelemetry.objects.get_or_create(vehicle=vehicle)
        for field, value in fields.items():
            setattr(telemetry, field, value)
        telemetry.save()
        updated += 1
    matched_imeis = {vehicle.imei for vehicle in vehicles}
    unmatched = len(by_imei) - len(matched_imeis)
    return {"matched": len(matched_imeis), "unmatched": unmatched, "updated": updated}
