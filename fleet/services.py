from django.db.models import Max

from accounts.constants import Level, Module, RoleCode
from accounts.services import user_can
from fleet.alerts import build_alerts
from fleet.constants import (
    DOCUMENT_LABELS,
    DOCUMENT_TYPES,
    FINANCE_DOCUMENT_TYPES,
    VehicleStatus,
)
from fleet.models import VehicleDocument
from fleet.platform import get_platform_settings
from fleet.status import (
    constituency_status,
    document_validity,
    is_exceeded,
    matches_filter,
    needs_attention,
    vehicle_status,
)


def media_url(request, field):
    if not field:
        return None
    url = field.url
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def _role_code(user):
    if getattr(user, "is_superuser", False):
        return RoleCode.SUPER_ADMIN
    role = getattr(user, "role", None)
    return role.code if role else None


def show_driver_contact(user):
    return user_can(user, Module.DRIVER_DETAILS, Level.VIEW) and _role_code(user) != RoleCode.FINANCE


def allowed_document_types(user):
    if _role_code(user) == RoleCode.FINANCE:
        return set(FINANCE_DOCUMENT_TYPES)
    return set(DOCUMENT_TYPES)


def compose_vehicle(vehicle, user=None, request=None, now=None, settings=None):
    cfg = settings or get_platform_settings()
    telemetry = getattr(vehicle, "telemetry", None)
    status = vehicle_status(telemetry, now, settings=cfg)
    today_km = telemetry.today_km if telemetry else 0
    attention = needs_attention(status, telemetry, now, settings=cfg)
    exceeded = is_exceeded(today_km, settings=cfg)
    constituency = vehicle.constituency
    driver = vehicle.driver
    include_contact = show_driver_contact(user) if user is not None else True
    return {
        "id": str(vehicle.id),
        "code": vehicle.code,
        "registration": vehicle.registration,
        "imei": vehicle.imei or "",
        "photo": media_url(request, vehicle.photo),
        "plate_photo": media_url(request, vehicle.plate_photo),
        "led_photo": media_url(request, vehicle.led_photo),
        "chassis_photo": media_url(request, vehicle.chassis_photo),
        "constituency": {
            "id": str(constituency.id),
            "code": constituency.code,
            "number": constituency.number,
            "name": constituency.name,
            "district": constituency.district,
            "district_label": constituency.district_label,
            "lat": constituency.lat,
            "lng": constituency.lng,
            "image": media_url(request, constituency.image),
        },
        "driver": {
            "id": str(driver.id),
            "name": driver.name,
            "photo": media_url(request, driver.photo),
            "phone": driver.phone if include_contact else None,
            "licence_number": driver.licence_number if include_contact else None,
            "licence_expiry": driver.licence_expiry.isoformat() if include_contact and driver.licence_expiry else None,
            "duty_status": driver.duty_status,
            "contact_restricted": not include_contact,
        },
        "telemetry": {
            "lat": telemetry.lat if telemetry else None,
            "lng": telemetry.lng if telemetry else None,
            "address": telemetry.address if telemetry else "",
            "speed_kmh": telemetry.speed_kmh if telemetry else 0,
            "ignition": telemetry.ignition if telemetry else False,
            "led_on": telemetry.led_on if telemetry else False,
            "gps_connected": telemetry.gps_connected if telemetry else False,
            "last_update": telemetry.last_update.isoformat() if telemetry and telemetry.last_update else None,
            "trip_started": telemetry.trip_started if telemetry else False,
        },
        "status": status,
        "attention": attention,
        "exceeded": exceeded,
        "today_km": round(float(today_km), 1),
        "daily_km_limit": cfg.daily_km_limit,
        "long_halt_minutes": cfg.long_halt_minutes,
        "stale_gps_minutes": cfg.stale_gps_minutes,
        "operating_min": telemetry.operating_min if telemetry else 0,
    }


def compose_documents(vehicle, user=None, request=None, now=None, settings=None):
    allowed = allowed_document_types(user) if user is not None else set(DOCUMENT_TYPES)
    by_type = {item.doc_type: item for item in vehicle.documents.all()}
    rows = []
    for doc_type in DOCUMENT_TYPES:
        if doc_type not in allowed:
            continue
        document = by_type.get(doc_type)
        rows.append(serialize_document(document, doc_type, request=request, now=now, settings=settings))
    return rows


def serialize_document(document, doc_type, request=None, now=None, settings=None):
    reviewer = None
    if document and document.reviewed_by_id:
        reviewer = document.reviewed_by.full_name or document.reviewed_by.email
    return {
        "type": doc_type,
        "label": DOCUMENT_LABELS[doc_type],
        "file": media_url(request, document.file) if document else None,
        "file_name": document.file_name if document else "",
        "start_date": document.start_date.isoformat() if document and document.start_date else None,
        "end_date": document.end_date.isoformat() if document and document.end_date else None,
        "approval": document.approval if document else None,
        "review_comment": document.review_comment if document else "",
        "reviewed_at": document.reviewed_at.isoformat() if document and document.reviewed_at else None,
        "reviewed_by": reviewer,
        "validity": document_validity(document, now, settings=settings),
    }


def compose_vehicle_detail(vehicle, user, request=None, now=None, settings=None):
    cfg = settings or get_platform_settings()
    live = compose_vehicle(vehicle, user=user, request=request, now=now, settings=cfg)
    live["documents"] = compose_documents(vehicle, user=user, request=request, now=now, settings=cfg)
    live["alerts"] = build_alerts(vehicle, now)
    live["quick_actions"] = {
        "live_map": f"/live-map?vehicle={vehicle.id}",
        "history": f"/history?vehicle={vehicle.id}",
        "share": None,
        "notifications": f"/alerts?vehicle={vehicle.id}",
    }
    return live


def vehicle_rows_for(vehicles, user=None, request=None, now=None, settings=None):
    cfg = settings or get_platform_settings()
    return [compose_vehicle(vehicle, user=user, request=request, now=now, settings=cfg) for vehicle in vehicles]


def rollup_constituency(constituency, vehicles, user=None, request=None, now=None, settings=None):
    cfg = settings or get_platform_settings()
    rows = vehicle_rows_for(vehicles, user=user, request=request, now=now, settings=cfg)
    status = constituency_status(rows)
    return {
        "id": str(constituency.id),
        "code": constituency.code,
        "number": constituency.number,
        "name": constituency.name,
        "district": constituency.district,
        "district_label": constituency.district_label,
        "lat": constituency.lat,
        "lng": constituency.lng,
        "image": media_url(request, constituency.image),
        "total": len(rows),
        "active": sum(1 for row in rows if row["status"] == VehicleStatus.ACTIVE),
        "inactive": sum(1 for row in rows if row["status"] == VehicleStatus.INACTIVE),
        "attention": sum(1 for row in rows if row["attention"]),
        "exceeded": sum(1 for row in rows if row["exceeded"]),
        "today_km": round(sum(row["today_km"] for row in rows), 1),
        "status": status,
        "vehicles": rows,
    }


def filter_vehicles(rows, query="", constituency_id="all", status="all"):
    q = query.strip().lower()
    filtered = []
    for row in rows:
        if constituency_id not in ("", "all") and row["constituency"]["id"] != str(constituency_id):
            continue
        if status not in ("", "all") and not matches_filter(
            status, row["status"], row["attention"], row["exceeded"]
        ):
            continue
        if q and q not in f"{row['code']} {row['registration']} {row['driver']['name']}".lower():
            continue
        filtered.append(row)
    return filtered


def filter_constituencies(rows, query="", status="all", ordering="code"):
    q = query.strip().lower()
    filtered = []
    for row in rows:
        if status not in ("", "all") and row["status"] != status:
            continue
        haystack = f"{row['name']} {row['code']} {row['number']}".lower()
        if q and q not in haystack:
            continue
        filtered.append(row)
    reverse = ordering.startswith("-")
    key = ordering.lstrip("-")
    if key == "name":
        filtered.sort(key=lambda item: item["name"].lower(), reverse=reverse)
    else:
        filtered.sort(key=lambda item: item["number"], reverse=reverse)
    return filtered


def ensure_vehicle_documents(vehicle):
    existing = set(vehicle.documents.values_list("doc_type", flat=True))
    for doc_type in DOCUMENT_TYPES:
        if doc_type not in existing:
            VehicleDocument.objects.create(vehicle=vehicle, doc_type=doc_type)
    vehicle.refresh_from_db()


def next_constituency_number():
    from fleet.models import Constituency

    current = Constituency.objects.aggregate(max_number=Max("number"))["max_number"]
    return (current or 0) + 1


def next_vehicle_serial(constituency):
    from fleet.constants import format_vehicle_code

    serial = 1
    while serial <= 99:
        code = format_vehicle_code(constituency.district, constituency.number, serial)
        if not vehicle_code_exists(code):
            return serial
        serial += 1
    return serial


def vehicle_code_exists(code):
    from fleet.models import Vehicle

    return Vehicle.objects.filter(code=code).exists()
