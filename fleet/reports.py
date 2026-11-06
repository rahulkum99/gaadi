from datetime import timedelta

from django.utils import timezone

from accounts.constants import RoleCode
from fleet.constants import FINANCE_REPORT_KINDS, REPORT_KINDS, ReportKind, VehicleStatus
from fleet.dates import date_span, local_day_bounds, parse_query_date
from fleet.history import format_duration, vehicle_day_stats
from fleet.models import AlertEvent
from fleet.platform import get_platform_settings
from fleet.scoping import scoped_vehicles
from fleet.status import vehicle_status


def _role_code(user):
    from accounts.services import is_super_admin

    if is_super_admin(user):
        return RoleCode.SUPER_ADMIN
    role = getattr(user, "role", None)
    return role.code if role else None


def allowed_report_kinds(user):
    if _role_code(user) == RoleCode.FINANCE:
        return list(FINANCE_REPORT_KINDS)
    return list(REPORT_KINDS)


def can_export_reports(user):
    from accounts.constants import Level, Module
    from accounts.services import user_can

    return user_can(user, Module.EXPORT_DATA, Level.VIEW)


def _vehicles(user):
    return list(scoped_vehicles(user).select_related("constituency", "driver", "telemetry"))


def _day_stats_map(vehicles, day, settings, now):
    return {vehicle.id: vehicle_day_stats(vehicle, day, settings=settings, now=now) for vehicle in vehicles}


def _alerts_for_day(vehicle_ids, day):
    if not vehicle_ids:
        return []
    start, end = local_day_bounds(day)
    return list(
        AlertEvent.objects.filter(
            vehicle_id__in=vehicle_ids,
            occurred_at__gte=start,
            occurred_at__lt=end,
        ).select_related("vehicle__constituency")
    )


def build_daily_report(user, day, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    vehicles = _vehicles(user)
    stats = _day_stats_map(vehicles, day, cfg, now)
    alerts = _alerts_for_day([vehicle.id for vehicle in vehicles], day)
    active = sum(1 for row in stats.values() if row["status"] != VehicleStatus.INACTIVE)
    inactive = len(vehicles) - active
    total_km = round(sum(row["km"] for row in stats.values()), 1)
    operating = sum(row["operating_min"] for row in stats.values())
    halts = sum(row["stops"] for row in stats.values())
    constituencies = {}
    for vehicle in vehicles:
        row = stats[vehicle.id]
        bucket = constituencies.setdefault(
            vehicle.constituency_id,
            {
                "id": str(vehicle.constituency_id),
                "code": vehicle.constituency.code,
                "name": vehicle.constituency.name,
                "vehicles": 0,
                "km": 0.0,
            },
        )
        bucket["vehicles"] += 1
        bucket["km"] = round(bucket["km"] + row["km"], 1)
    constituency_rows = sorted(constituencies.values(), key=lambda item: item["km"], reverse=True)
    trend = []
    for trend_day in date_span(day - timedelta(days=6), day):
        day_km = sum(vehicle_day_stats(vehicle, trend_day, settings=cfg, now=now)["km"] for vehicle in vehicles)
        trend.append({"date": trend_day.isoformat(), "km": round(day_km, 1)})
    avg_trend = round(sum(item["km"] for item in trend) / max(len(trend), 1), 1)
    return {
        "kind": "daily",
        "date": day.isoformat(),
        "kpis": {
            "total_km": total_km,
            "active": active,
            "inactive": inactive,
            "operating_min": operating,
            "operating": format_duration(operating),
            "halts": halts,
            "alerts": len(alerts),
        },
        "trend": trend,
        "average_km": avg_trend,
        "top_constituencies": constituency_rows[:10],
        "constituencies": constituency_rows,
    }


def build_constituency_report(user, day, constituency_id=None, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    vehicles = _vehicles(user)
    if constituency_id not in (None, "", "all"):
        vehicles = [vehicle for vehicle in vehicles if str(vehicle.constituency_id) == str(constituency_id)]
    stats = _day_stats_map(vehicles, day, cfg, now)
    alerts = _alerts_for_day([vehicle.id for vehicle in vehicles], day)
    alerts_by_constituency = {}
    for event in alerts:
        alerts_by_constituency[event.vehicle.constituency_id] = (
            alerts_by_constituency.get(event.vehicle.constituency_id, 0) + 1
        )
    grouped = {}
    for vehicle in vehicles:
        row = stats[vehicle.id]
        bucket = grouped.setdefault(
            vehicle.constituency_id,
            {
                "id": str(vehicle.constituency_id),
                "code": vehicle.constituency.code,
                "name": vehicle.constituency.name,
                "assigned": 0,
                "active": 0,
                "inactive": 0,
                "total_km": 0.0,
                "alerts": alerts_by_constituency.get(vehicle.constituency_id, 0),
            },
        )
        bucket["assigned"] += 1
        if row["status"] == VehicleStatus.INACTIVE:
            bucket["inactive"] += 1
        else:
            bucket["active"] += 1
        bucket["total_km"] = round(bucket["total_km"] + row["km"], 1)
    rows = []
    for bucket in grouped.values():
        bucket["avg_km"] = round(bucket["total_km"] / bucket["assigned"], 1) if bucket["assigned"] else 0
        rows.append(bucket)
    rows.sort(key=lambda item: item["code"])
    return {"kind": "constituency", "date": day.isoformat(), "rows": rows}


def build_vehicle_report(user, day, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    vehicles = _vehicles(user)
    stats = _day_stats_map(vehicles, day, cfg, now)
    alerts = _alerts_for_day([vehicle.id for vehicle in vehicles], day)
    alert_counts = {}
    for event in alerts:
        alert_counts[event.vehicle_id] = alert_counts.get(event.vehicle_id, 0) + 1
    rows = []
    for vehicle in vehicles:
        row = stats[vehicle.id]
        live_status = vehicle_status(getattr(vehicle, "telemetry", None), now, settings=cfg)
        rows.append(
            {
                "id": str(vehicle.id),
                "code": vehicle.code,
                "registration": vehicle.registration,
                "constituency": vehicle.constituency.name,
                "constituency_code": vehicle.constituency.code,
                "driver": vehicle.driver.name,
                "km": row["km"],
                "operating": row["operating"],
                "operating_min": row["operating_min"],
                "stops": row["stops"],
                "halts": row["long_halts"],
                "alerts": alert_counts.get(vehicle.id, 0),
                "status": live_status if day == timezone.localdate(now) else row["status"],
            }
        )
    return {"kind": "vehicle", "date": day.isoformat(), "rows": rows}


def build_route_report(user, day, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    rows = []
    for vehicle in _vehicles(user):
        stats = vehicle_day_stats(vehicle, day, settings=cfg, now=now)
        if stats["empty"] or stats["km"] <= 0:
            continue
        rows.append(
            {
                "id": str(vehicle.id),
                "code": vehicle.code,
                "registration": vehicle.registration,
                "start": stats["start"],
                "end": stats["end"],
                "km": stats["km"],
                "operating": stats["operating"],
                "operating_min": stats["operating_min"],
                "halt": stats["halt"],
                "halt_min": stats["halt_min"],
                "stops": stats["stops"],
            }
        )
    return {"kind": "route", "date": day.isoformat(), "rows": rows}


def build_alert_report(user, day, settings=None, now=None):
    from fleet.alerts import alert_label, count_alerts, serialize_alert

    cfg = settings or get_platform_settings()
    vehicles = _vehicles(user)
    events = _alerts_for_day([vehicle.id for vehicle in vehicles], day)
    rows = [
        {
            "time": event.occurred_at.isoformat() if event.occurred_at else None,
            "type": event.alert_type,
            "label": alert_label(event.alert_type, cfg),
            "vehicle": event.vehicle.code,
            "vehicle_id": str(event.vehicle_id),
            "constituency": event.vehicle.constituency.name,
            "description": event.description,
        }
        for event in events
    ]
    serialized = [serialize_alert(event, settings=cfg) for event in events]
    return {
        "kind": "alert",
        "date": day.isoformat(),
        "kpis": count_alerts(serialized),
        "rows": rows,
    }


def build_report(user, kind, params):
    if kind not in allowed_report_kinds(user):
        return None, "This report is not available for your role."
    now = timezone.now()
    cfg = get_platform_settings()
    day = parse_query_date(params.get("date"))
    if day is None:
        return None, "Unknown date."
    if kind == ReportKind.DAILY:
        return build_daily_report(user, day, settings=cfg, now=now), None
    if kind == ReportKind.CONSTITUENCY:
        return build_constituency_report(
            user, day, constituency_id=params.get("constituency"), settings=cfg, now=now
        ), None
    if kind == ReportKind.VEHICLE:
        return build_vehicle_report(user, day, settings=cfg, now=now), None
    if kind == ReportKind.ROUTE:
        return build_route_report(user, day, settings=cfg, now=now), None
    if kind == ReportKind.ALERT:
        return build_alert_report(user, day, settings=cfg, now=now), None
    return None, "Unknown report."
