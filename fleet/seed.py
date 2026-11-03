from datetime import timedelta

from django.utils import timezone

from fleet.constants import (
    DOCUMENT_TYPES,
    GOA_CONSTITUENCIES,
    ApprovalStatus,
    DocumentType,
    DutyStatus,
    constituency_code,
    format_vehicle_code,
)
from fleet.models import Constituency, Driver, Vehicle, VehicleDocument, VehicleTelemetry


def seed_goa_constituencies():
    created = 0
    for number, name, district, lat, lng in GOA_CONSTITUENCIES:
        _, was_created = Constituency.objects.get_or_create(
            number=number,
            defaults={
                "code": constituency_code(number),
                "name": name,
                "district": district,
                "lat": lat,
                "lng": lng,
            },
        )
        created += int(was_created)
    return created


def _ensure_documents(vehicle, specs):
    today = timezone.now().date()
    for doc_type in DOCUMENT_TYPES:
        spec = specs.get(doc_type, {})
        VehicleDocument.objects.get_or_create(
            vehicle=vehicle,
            doc_type=doc_type,
            defaults={
                "file_name": spec.get("file_name", ""),
                "start_date": spec.get("start_date"),
                "end_date": spec.get("end_date", today + timedelta(days=180)),
                "approval": spec.get("approval"),
            },
        )


def seed_demo_fleet():
    now = timezone.now()
    today = now.date()
    seed_goa_constituencies()
    mandrem = Constituency.objects.get(number=1)
    panaji = Constituency.objects.get(number=11)
    margao = Constituency.objects.get(number=31)

    demo = (
        {
            "constituency": mandrem,
            "serial": 1,
            "registration": "GA08AA1001",
            "driver": "Ravi Naik",
            "phone": "9822123001",
            "telemetry": {
                "lat": mandrem.lat,
                "lng": mandrem.lng,
                "address": "Mandrem beach road",
                "speed_kmh": 28,
                "ignition": True,
                "led_on": True,
                "gps_connected": True,
                "last_update": now,
                "trip_started": True,
                "today_km": 22.4,
                "operating_min": 140,
            },
            "documents": {
                DocumentType.RC: {
                    "file_name": "rc.pdf",
                    "approval": ApprovalStatus.APPROVED,
                    "end_date": today + timedelta(days=200),
                },
                DocumentType.INSURANCE: {
                    "file_name": "insurance.pdf",
                    "approval": ApprovalStatus.PENDING,
                    "end_date": today + timedelta(days=18),
                },
            },
        },
        {
            "constituency": mandrem,
            "serial": 2,
            "registration": "GA08AA1002",
            "driver": "Suresh Kamat",
            "phone": "9822123002",
            "telemetry": {
                "lat": mandrem.lat,
                "lng": mandrem.lng,
                "address": "Pernem-Mandrem junction",
                "speed_kmh": 0,
                "ignition": True,
                "led_on": True,
                "gps_connected": True,
                "last_update": now - timedelta(minutes=90),
                "trip_started": True,
                "today_km": 14.1,
                "operating_min": 90,
            },
            "documents": {},
        },
        {
            "constituency": panaji,
            "serial": 1,
            "registration": "GA07BB2101",
            "driver": "Anita Dessai",
            "phone": "9822123011",
            "telemetry": {
                "lat": panaji.lat,
                "lng": panaji.lng,
                "address": "Panaji bus stand",
                "speed_kmh": 0,
                "ignition": False,
                "led_on": False,
                "gps_connected": False,
                "last_update": now - timedelta(hours=8),
                "trip_started": False,
                "today_km": 0,
                "operating_min": 0,
            },
            "documents": {
                DocumentType.FITNESS: {
                    "file_name": "fitness.pdf",
                    "approval": ApprovalStatus.REJECTED,
                    "end_date": today - timedelta(days=4),
                },
            },
        },
        {
            "constituency": panaji,
            "serial": 2,
            "registration": "GA07BB2102",
            "driver": "John Fernandes",
            "phone": "9822123012",
            "telemetry": {
                "lat": panaji.lat,
                "lng": panaji.lng,
                "address": "Miramar circle",
                "speed_kmh": 18,
                "ignition": True,
                "led_on": False,
                "gps_connected": True,
                "last_update": now,
                "trip_started": True,
                "today_km": 31.0,
                "operating_min": 200,
            },
            "documents": {},
        },
        {
            "constituency": margao,
            "serial": 1,
            "registration": "GA08CC3101",
            "driver": "Priya Naik",
            "phone": "9822123031",
            "telemetry": {
                "lat": margao.lat,
                "lng": margao.lng,
                "address": "Margao market",
                "speed_kmh": 22,
                "ignition": True,
                "led_on": True,
                "gps_connected": True,
                "last_update": now,
                "trip_started": True,
                "today_km": 71.5,
                "operating_min": 260,
            },
            "documents": {
                DocumentType.ADVERTISEMENT_LICENSE: {
                    "file_name": "ad-license.pdf",
                    "approval": ApprovalStatus.APPROVED,
                    "end_date": today + timedelta(days=45),
                },
            },
        },
        {
            "constituency": margao,
            "serial": 2,
            "registration": "GA08CC3102",
            "driver": "Imran Shaikh",
            "phone": "9822123032",
            "telemetry": {
                "lat": margao.lat,
                "lng": margao.lng,
                "address": "Fatorda stadium road",
                "speed_kmh": 12,
                "ignition": True,
                "led_on": True,
                "gps_connected": False,
                "last_update": now - timedelta(minutes=25),
                "trip_started": True,
                "today_km": 19.8,
                "operating_min": 110,
            },
            "documents": {},
        },
    )

    created = 0
    for item in demo:
        constituency = item["constituency"]
        code = format_vehicle_code(constituency.district, constituency.number, item["serial"])
        driver, _ = Driver.objects.get_or_create(
            name=item["driver"],
            defaults={
                "phone": item["phone"],
                "licence_number": f"GA{item['serial']:02d} 100000{item['serial']}",
                "licence_expiry": today + timedelta(days=400),
                "duty_status": (
                    DutyStatus.ON_DUTY
                    if item["telemetry"]["trip_started"]
                    else DutyStatus.OFF_DUTY
                ),
            },
        )
        vehicle, was_created = Vehicle.objects.get_or_create(
            code=code,
            defaults={
                "registration": item["registration"],
                "constituency": constituency,
                "driver": driver,
            },
        )
        VehicleTelemetry.objects.update_or_create(
            vehicle=vehicle,
            defaults=item["telemetry"],
        )
        _ensure_documents(vehicle, item["documents"])
        created += int(was_created)
    return created
