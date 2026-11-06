from django.utils import timezone

from fleet.constants import VehicleStatus
from fleet.dates import date_span, local_day_bounds
from fleet.models import VehicleGpsPoint
from fleet.platform import get_platform_settings


def format_duration(minutes):
    minutes = int(minutes or 0)
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    if hours:
        return f"{hours}h"
    return f"{rest}m"


def _points_for_day(vehicle, day):
    start, end = local_day_bounds(day)
    return list(
        VehicleGpsPoint.objects.filter(
            vehicle=vehicle,
            captured_at__gte=start,
            captured_at__lt=end,
        ).order_by("captured_at")
    )


def _synthetic_point(vehicle, now):
    telemetry = getattr(vehicle, "telemetry", None)
    if telemetry is None:
        return None
    return VehicleGpsPoint(
        vehicle=vehicle,
        captured_at=telemetry.last_update or now,
        lat=telemetry.lat,
        lng=telemetry.lng,
        address=telemetry.address or "",
        speed_kmh=telemetry.speed_kmh or 0,
        ignition=telemetry.ignition,
        led_on=telemetry.led_on,
        gps_connected=telemetry.gps_connected,
        today_km=telemetry.today_km or 0,
        operating_min=telemetry.operating_min or 0,
    )


def extract_stops(points, settings):
    if not points:
        return []
    stops = []
    halt_start = None
    halt_point = None
    last_moving_km = points[0].today_km or 0
    for point in points:
        stopped = (point.speed_kmh or 0) <= 2
        if stopped and halt_start is None:
            halt_start = point.captured_at
            halt_point = point
        elif not stopped and halt_start is not None:
            duration = (point.captured_at - halt_start).total_seconds() / 60
            if duration >= settings.min_stop_minutes:
                stops.append(_stop_row(len(stops) + 1, halt_point, halt_start, point.captured_at, duration, last_moving_km, settings))
            halt_start = None
            halt_point = None
            last_moving_km = point.today_km or last_moving_km
        elif not stopped:
            last_moving_km = point.today_km or last_moving_km
    if halt_start is not None and halt_point is not None:
        duration = (points[-1].captured_at - halt_start).total_seconds() / 60
        if duration >= settings.min_stop_minutes:
            stops.append(
                _stop_row(
                    len(stops) + 1,
                    halt_point,
                    halt_start,
                    None,
                    duration,
                    last_moving_km,
                    settings,
                )
            )
    return stops


def _stop_row(number, point, arrived, departed, duration, km_so_far, settings):
    return {
        "number": number,
        "location": point.address or "",
        "lat": point.lat,
        "lng": point.lng,
        "arrival": arrived.isoformat() if arrived else None,
        "departure": departed.isoformat() if departed else None,
        "duration_min": int(round(duration)),
        "duration": format_duration(duration),
        "km_so_far": round(float(km_so_far or 0), 1),
        "long_halt": duration >= settings.long_halt_minutes,
    }


def day_status(points, stops, settings, now=None):
    if not points:
        return VehicleStatus.INACTIVE
    started = any(
        (point.speed_kmh or 0) > 2 or point.ignition or (point.today_km or 0) > 0.05 for point in points
    )
    if not started:
        return VehicleStatus.INACTIVE
    if any(stop["long_halt"] for stop in stops):
        return VehicleStatus.LONG_HALT
    return VehicleStatus.ACTIVE


def vehicle_day_stats(vehicle, day, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    points = _points_for_day(vehicle, day)
    if not points and day == timezone.localdate(now):
        synthetic = _synthetic_point(vehicle, now)
        if synthetic is not None:
            points = [synthetic]
    stops = extract_stops(points, cfg)
    if not points:
        return {
            "date": day.isoformat(),
            "start": None,
            "end": None,
            "km": 0,
            "operating_min": 0,
            "operating": format_duration(0),
            "halt_min": 0,
            "halt": format_duration(0),
            "stops": 0,
            "long_halts": 0,
            "status": VehicleStatus.INACTIVE,
            "points": [],
            "stop_rows": [],
            "empty": True,
        }
    first_active = next((p for p in points if (p.speed_kmh or 0) > 2 or p.ignition or (p.today_km or 0) > 0.05), points[0])
    last = points[-1]
    halt_min = sum(stop["duration_min"] for stop in stops)
    return {
        "date": day.isoformat(),
        "start": first_active.captured_at.isoformat() if first_active.captured_at else None,
        "end": last.captured_at.isoformat() if last.captured_at else None,
        "km": round(float(last.today_km or 0), 1),
        "operating_min": int(last.operating_min or 0),
        "operating": format_duration(last.operating_min),
        "halt_min": halt_min,
        "halt": format_duration(halt_min),
        "stops": len(stops),
        "long_halts": sum(1 for stop in stops if stop["long_halt"]),
        "status": day_status(points, stops, cfg, now),
        "points": points,
        "stop_rows": stops,
        "empty": False,
    }


def summarize_days(day_rows):
    total_km = sum(row["km"] for row in day_rows)
    days_with_km = [row for row in day_rows if row["km"] or not row["empty"]]
    count = max(len(day_rows), 1)
    operating = sum(row["operating_min"] for row in day_rows)
    halt = sum(row["halt_min"] for row in day_rows)
    stops = sum(row["stops"] for row in day_rows)
    long_halts = sum(row["long_halts"] for row in day_rows)
    return {
        "total_km": round(total_km, 1),
        "avg_km": round(total_km / count, 1),
        "operating_min": operating,
        "operating": format_duration(operating),
        "halt_min": halt,
        "halt": format_duration(halt),
        "stops": stops,
        "long_halts": long_halts,
        "days_active": len(days_with_km),
    }


def serialize_point(point):
    return {
        "captured_at": point.captured_at.isoformat() if point.captured_at else None,
        "lat": point.lat,
        "lng": point.lng,
        "speed_kmh": point.speed_kmh,
        "today_km": point.today_km,
        "address": point.address,
    }


def build_history_list(vehicle, start, end, settings=None, now=None):
    cfg = settings or get_platform_settings()
    days = date_span(start, end)
    rows = [vehicle_day_stats(vehicle, day, settings=cfg, now=now) for day in days]
    kpis = summarize_days(rows)
    chart = [{"date": row["date"], "km": row["km"]} for row in rows]
    table = [
        {
            "date": row["date"],
            "start": row["start"],
            "end": row["end"],
            "km": row["km"],
            "operating": row["operating"],
            "operating_min": row["operating_min"],
            "halt": row["halt"],
            "halt_min": row["halt_min"],
            "stops": row["stops"],
            "long_halts": row["long_halts"],
            "status": row["status"],
        }
        for row in rows
    ]
    return {
        "vehicle": {
            "id": str(vehicle.id),
            "code": vehicle.code,
            "registration": vehicle.registration,
        },
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "kpis": kpis,
        "chart": chart,
        "average_km": kpis["avg_km"],
        "days": table,
    }


def build_history_day(vehicle, day, settings=None, now=None):
    cfg = settings or get_platform_settings()
    stats = vehicle_day_stats(vehicle, day, settings=cfg, now=now)
    points = stats["points"]
    polyline = [
        {"lat": point.lat, "lng": point.lng, "captured_at": point.captured_at.isoformat()}
        for point in points
        if point.lat is not None and point.lng is not None
    ]
    start_point = polyline[0] if polyline else None
    end_point = polyline[-1] if polyline else None
    return {
        "vehicle": {
            "id": str(vehicle.id),
            "code": vehicle.code,
            "registration": vehicle.registration,
        },
        "date": day.isoformat(),
        "empty": stats["empty"],
        "kpis": {
            "km": stats["km"],
            "operating": stats["operating"],
            "operating_min": stats["operating_min"],
            "halt": stats["halt"],
            "halt_min": stats["halt_min"],
            "stops": stats["stops"],
            "long_halts": stats["long_halts"],
        },
        "start": start_point,
        "end": end_point,
        "polyline": polyline,
        "stops": stats["stop_rows"],
        "points": [serialize_point(point) for point in points],
    }


def build_timeline(vehicle, day, settings=None, now=None):
    cfg = settings or get_platform_settings()
    stats = vehicle_day_stats(vehicle, day, settings=cfg, now=now)
    items = []
    if stats["start"]:
        items.append(
            {
                "kind": "vehicle_started",
                "label": "Vehicle started",
                "at": stats["start"],
                "address": stats["points"][0].address if stats["points"] else "",
            }
        )
    for stop in stats["stop_rows"]:
        items.append(
            {
                "kind": "long_halt" if stop["long_halt"] else "stop",
                "label": "Long halt" if stop["long_halt"] else "Stop",
                "at": stop["arrival"],
                "address": stop["location"],
                "duration": stop["duration"],
                "duration_min": stop["duration_min"],
            }
        )
    if stats["points"]:
        last = stats["points"][-1]
        items.append(
            {
                "kind": "last_point",
                "label": "Last recorded point",
                "at": last.captured_at.isoformat() if last.captured_at else stats["end"],
                "address": last.address,
            }
        )
    return items
