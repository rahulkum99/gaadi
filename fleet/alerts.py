from fleet.constants import (
    ALERT_LABELS,
    ALERT_SEVERITY,
    AlertType,
    VehicleStatus,
)
from fleet.status import is_exceeded, is_gps_stale, vehicle_status


def build_alerts(vehicle, now=None):
    telemetry = getattr(vehicle, "telemetry", None)
    status = vehicle_status(telemetry, now)
    today_km = telemetry.today_km if telemetry else 0
    events = []

    def push(alert_type, created_at, extra=""):
        label = ALERT_LABELS[alert_type]
        events.append(
            {
                "id": f"{vehicle.code}-{alert_type}",
                "type": alert_type,
                "severity": ALERT_SEVERITY[alert_type],
                "vehicle_id": str(vehicle.id),
                "vehicle_code": vehicle.code,
                "constituency_id": str(vehicle.constituency_id),
                "created_at": created_at,
                "description": f"{label}. {extra}".strip() if extra else label,
                "lat": telemetry.lat if telemetry else None,
                "lng": telemetry.lng if telemetry else None,
            }
        )

    if telemetry is None:
        return events

    created_at = telemetry.last_update
    if is_exceeded(today_km):
        push(AlertType.KM_EXCEEDED, created_at, f"Today's distance is {today_km:.1f} km.")
    if status == VehicleStatus.LONG_HALT:
        push(AlertType.LONG_HALT, created_at)
    if status != VehicleStatus.INACTIVE and not telemetry.led_on:
        push(AlertType.LED_OFF, created_at, "LED branding screen is off while the vehicle is on duty.")
    if is_gps_stale(telemetry, now):
        push(AlertType.GPS_DISCONNECTED, created_at, "No recent GPS update from the tracking device.")
    return events
