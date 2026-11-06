from django.utils import timezone

from fleet.constants import (
    ALERT_KPI_TYPES,
    ALERT_LABELS,
    ALERT_SEVERITY,
    UNREAD_ALERT_SEVERITIES,
    AlertType,
    VehicleStatus,
)
from fleet.models import AlertEvent
from fleet.platform import get_platform_settings
from fleet.status import halt_anchor, is_exceeded, is_gps_stale, minutes_since, vehicle_status


def alert_label(alert_type, settings=None):
    if alert_type == AlertType.KM_EXCEEDED:
        cfg = settings or get_platform_settings()
        return f"{int(cfg.daily_km_limit)} km daily limit exceeded"
    return ALERT_LABELS[alert_type]


def _dedupe_key(vehicle, alert_type, suffix):
    return f"{vehicle.id}:{alert_type}:{suffix}"


def ensure_alert(vehicle, alert_type, occurred_at, telemetry, settings, extra="", dedupe_suffix=""):
    key = _dedupe_key(vehicle, alert_type, dedupe_suffix)
    label = alert_label(alert_type, settings)
    description = f"{label}. {extra}".strip() if extra else label
    defaults = {
        "vehicle": vehicle,
        "alert_type": alert_type,
        "severity": ALERT_SEVERITY[alert_type],
        "description": description,
        "occurred_at": occurred_at,
        "lat": telemetry.lat if telemetry else None,
        "lng": telemetry.lng if telemetry else None,
        "address": telemetry.address if telemetry else "",
        "today_km": telemetry.today_km if telemetry else 0,
        "speed_kmh": telemetry.speed_kmh if telemetry else 0,
    }
    event, created = AlertEvent.objects.get_or_create(dedupe_key=key, defaults=defaults)
    if not created and event.resolved_at is not None:
        event.resolved_at = None
        event.description = description
        event.occurred_at = occurred_at
        event.lat = defaults["lat"]
        event.lng = defaults["lng"]
        event.address = defaults["address"]
        event.today_km = defaults["today_km"]
        event.speed_kmh = defaults["speed_kmh"]
        event.save()
    return 1 if created else 0


def resolve_open_alerts(vehicle, alert_type, now):
    updated = AlertEvent.objects.filter(
        vehicle=vehicle,
        alert_type=alert_type,
        resolved_at__isnull=True,
        dedupe_key__endswith=":open",
    ).update(resolved_at=now)
    if not updated:
        return
    for event in AlertEvent.objects.filter(
        vehicle=vehicle,
        alert_type=alert_type,
        resolved_at=now,
        dedupe_key__endswith=":open",
    ):
        event.dedupe_key = f"{event.dedupe_key}:{event.id}"
        event.save(update_fields=["dedupe_key"])


def evaluate_vehicle_alerts(vehicle, telemetry, settings=None, now=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    if telemetry is None:
        return 0
    created = 0
    local_date = timezone.localdate(now)
    status = vehicle_status(telemetry, now, settings=cfg)
    occurred_at = telemetry.last_update or now

    if telemetry.trip_started:
        created += ensure_alert(
            vehicle,
            AlertType.VEHICLE_STARTED,
            occurred_at,
            telemetry,
            cfg,
            extra="First recorded start of the day.",
            dedupe_suffix=str(local_date),
        )

    anchor = halt_anchor(telemetry)
    halted_for = minutes_since(anchor, now) if telemetry.trip_started else None
    if telemetry.trip_started and telemetry.speed_kmh <= 2 and halted_for is not None:
        halt_stamp = (anchor or occurred_at).isoformat()
        if halted_for >= cfg.min_stop_minutes:
            created += ensure_alert(
                vehicle,
                AlertType.VEHICLE_STOPPED,
                occurred_at,
                telemetry,
                cfg,
                extra=f"Stopped for {int(halted_for)} min at {telemetry.address or 'the last known location'}.",
                dedupe_suffix=halt_stamp,
            )
        if halted_for >= cfg.long_halt_minutes:
            created += ensure_alert(
                vehicle,
                AlertType.LONG_HALT,
                occurred_at,
                telemetry,
                cfg,
                extra=f"Stationary for {int(halted_for)} min.",
                dedupe_suffix=halt_stamp,
            )

    if is_exceeded(telemetry.today_km, settings=cfg):
        created += ensure_alert(
            vehicle,
            AlertType.KM_EXCEEDED,
            occurred_at,
            telemetry,
            cfg,
            extra=f"Today's distance is {telemetry.today_km:.1f} km.",
            dedupe_suffix=str(local_date),
        )

    if status != VehicleStatus.INACTIVE and not telemetry.led_on:
        created += ensure_alert(
            vehicle,
            AlertType.LED_OFF,
            occurred_at,
            telemetry,
            cfg,
            extra="LED branding screen is off while the vehicle is on duty.",
            dedupe_suffix="open",
        )
    else:
        resolve_open_alerts(vehicle, AlertType.LED_OFF, now)

    if is_gps_stale(telemetry, now, settings=cfg):
        created += ensure_alert(
            vehicle,
            AlertType.GPS_DISCONNECTED,
            occurred_at,
            telemetry,
            cfg,
            extra="GPS off, or no recent update from the tracking device.",
            dedupe_suffix="open",
        )
    else:
        resolve_open_alerts(vehicle, AlertType.GPS_DISCONNECTED, now)
    return created


def serialize_alert(event, live=None, settings=None):
    vehicle = event.vehicle
    constituency = vehicle.constituency
    driver = vehicle.driver
    live = live or {}
    return {
        "id": str(event.id),
        "type": event.alert_type,
        "label": alert_label(event.alert_type, settings),
        "severity": event.severity,
        "vehicle_id": str(vehicle.id),
        "vehicle_code": vehicle.code,
        "registration": vehicle.registration,
        "constituency_id": str(vehicle.constituency_id),
        "constituency": constituency.name if constituency else "",
        "driver": {
            "id": str(driver.id) if driver else None,
            "name": driver.name if driver else "",
            "phone": driver.phone if driver else "",
        },
        "created_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "description": event.description,
        "lat": event.lat,
        "lng": event.lng,
        "address": event.address,
        "today_km": event.today_km,
        "speed_kmh": event.speed_kmh,
        "live_status": live.get("status"),
        "attention": live.get("attention"),
        "exceeded": live.get("exceeded"),
    }


def alerts_for_vehicle(vehicle, now=None, settings=None):
    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    telemetry = getattr(vehicle, "telemetry", None)
    evaluate_vehicle_alerts(vehicle, telemetry, settings=cfg, now=now)
    day = timezone.localdate(now)
    start, end = _day_bounds(day)
    events = AlertEvent.objects.filter(
        vehicle=vehicle,
        occurred_at__gte=start,
        occurred_at__lt=end,
    ).select_related("vehicle__constituency", "vehicle__driver")
    live = {
        "status": vehicle_status(telemetry, now, settings=cfg),
        "attention": None,
        "exceeded": is_exceeded(telemetry.today_km if telemetry else 0, settings=cfg),
    }
    from fleet.status import needs_attention

    live["attention"] = needs_attention(live["status"], telemetry, now, settings=cfg)
    return [serialize_alert(event, live=live, settings=cfg) for event in events]


def build_alerts(vehicle, now=None):
    return alerts_for_vehicle(vehicle, now=now)


def _day_bounds(day):
    from fleet.dates import local_day_bounds

    return local_day_bounds(day)


def empty_alert_counts():
    counts = {"total": 0}
    for alert_type in ALERT_KPI_TYPES:
        counts[alert_type] = 0
    return counts


def count_alerts(events):
    counts = empty_alert_counts()
    counts["total"] = len(events)
    for event in events:
        alert_type = event["type"] if isinstance(event, dict) else event.alert_type
        if alert_type in counts:
            counts[alert_type] += 1
    return counts


def is_unread_severity(severity):
    return severity in UNREAD_ALERT_SEVERITIES


def evaluate_scoped_alerts(user, now=None, settings=None):
    from fleet.scoping import scoped_vehicles

    now = now or timezone.now()
    cfg = settings or get_platform_settings()
    vehicles = list(scoped_vehicles(user).select_related("telemetry", "constituency", "driver"))
    for vehicle in vehicles:
        evaluate_vehicle_alerts(vehicle, getattr(vehicle, "telemetry", None), settings=cfg, now=now)
    return vehicles, cfg


def build_alerts_index(user, params, now=None):
    from fleet.constants import ALERT_TYPES
    from fleet.dates import local_day_bounds, parse_query_date
    from fleet.services import compose_vehicle

    now = now or timezone.now()
    query_date = parse_query_date(params.get("date"))
    if query_date is None:
        return None, "Unknown date."
    alert_type = params.get("type") or "all"
    if alert_type not in ("all", *ALERT_TYPES):
        return None, "Unknown alert type."
    focused_id = (params.get("vehicle") or "").strip() or None
    vehicles, cfg = evaluate_scoped_alerts(user, now=now)
    scoped_ids = [vehicle.id for vehicle in vehicles]
    if focused_id and focused_id not in {str(vehicle.id) for vehicle in vehicles}:
        focused_id = None
    start, end = local_day_bounds(query_date)
    base = AlertEvent.objects.filter(
        occurred_at__gte=start,
        occurred_at__lt=end,
        vehicle_id__in=scoped_ids,
    )
    if focused_id:
        base = base.filter(vehicle_id=focused_id)
    count_types = list(base.values_list("alert_type", flat=True))
    counts = empty_alert_counts()
    counts["total"] = len(count_types)
    for item in count_types:
        if item in counts:
            counts[item] += 1
    queryset = base.select_related(
        "vehicle__constituency",
        "vehicle__driver",
        "vehicle__telemetry",
    )
    if alert_type != "all":
        queryset = queryset.filter(alert_type=alert_type)
    live_by_id = {
        vehicle.id: compose_vehicle(vehicle, user=user, now=now, settings=cfg) for vehicle in vehicles
    }
    events = [serialize_alert(event, live=live_by_id.get(event.vehicle_id), settings=cfg) for event in queryset]
    unread = [event for event in events if is_unread_severity(event["severity"])]
    limit = params.get("limit")
    if limit:
        try:
            events = events[: max(int(limit), 0)]
        except (TypeError, ValueError):
            return None, "limit must be a number."
    return {
        "date": query_date.isoformat(),
        "focused_vehicle_id": focused_id,
        "counts": counts,
        "unread_count": len([event for event in events if is_unread_severity(event["severity"])])
        if not limit
        else len(unread),
        "recent": unread[:6],
        "alerts": events,
    }, None


def build_alert_detail(user, alert_id, now=None):
    from fleet.history import build_timeline
    from fleet.scoping import can_access_vehicle
    from fleet.services import compose_vehicle

    now = now or timezone.now()
    try:
        event = AlertEvent.objects.select_related(
            "vehicle__constituency",
            "vehicle__driver",
            "vehicle__telemetry",
        ).get(pk=alert_id)
    except (AlertEvent.DoesNotExist, ValueError):
        return None, "Alert not found."
    if not can_access_vehicle(user, event.vehicle):
        return None, "Alert not found."
    cfg = get_platform_settings()
    evaluate_vehicle_alerts(event.vehicle, getattr(event.vehicle, "telemetry", None), settings=cfg, now=now)
    event.refresh_from_db()
    live = compose_vehicle(event.vehicle, user=user, now=now, settings=cfg)
    payload = serialize_alert(event, live=live, settings=cfg)
    payload.update(
        {
            "daily_km_limit": cfg.daily_km_limit,
            "operating_min": live["operating_min"],
            "current_speed_kmh": live["telemetry"]["speed_kmh"],
            "current_status": live["status"],
            "links": {
                "live_map": f"/live-map?vehicle={event.vehicle_id}",
                "history": f"/history/{event.vehicle_id}/{timezone.localdate(event.occurred_at).isoformat()}",
            },
            "timeline": build_timeline(
                event.vehicle,
                timezone.localdate(event.occurred_at),
                settings=cfg,
                now=now,
            ),
        }
    )
    return payload, None

