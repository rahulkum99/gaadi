class District:
    NORTH_GOA = "north_goa"
    SOUTH_GOA = "south_goa"


DISTRICTS = (District.NORTH_GOA, District.SOUTH_GOA)

DISTRICT_LABELS = {
    District.NORTH_GOA: "North Goa",
    District.SOUTH_GOA: "South Goa",
}

DISTRICT_CODES = {
    District.NORTH_GOA: "NG",
    District.SOUTH_GOA: "SG",
}


class DutyStatus:
    ON_DUTY = "on_duty"
    OFF_DUTY = "off_duty"


DUTY_STATUSES = (DutyStatus.ON_DUTY, DutyStatus.OFF_DUTY)


class VehicleStatus:
    ACTIVE = "active"
    LONG_HALT = "long_halt"
    INACTIVE = "inactive"


VEHICLE_STATUSES = (VehicleStatus.ACTIVE, VehicleStatus.LONG_HALT, VehicleStatus.INACTIVE)


class FilterStatus:
    ACTIVE = "active"
    ATTENTION = "attention"
    INACTIVE = "inactive"
    EXCEEDED = "exceeded"
    LONG_HALT = "long_halt"


FILTER_STATUSES = (
    FilterStatus.ACTIVE,
    FilterStatus.ATTENTION,
    FilterStatus.INACTIVE,
    FilterStatus.EXCEEDED,
    FilterStatus.LONG_HALT,
)


class ConstituencyStatus:
    OPERATIONAL = "operational"
    NEEDS_ATTENTION = "needs_attention"
    INACTIVE = "inactive"


CONSTITUENCY_STATUSES = (
    ConstituencyStatus.OPERATIONAL,
    ConstituencyStatus.NEEDS_ATTENTION,
    ConstituencyStatus.INACTIVE,
)


class DocumentType:
    RC = "rc"
    INSURANCE = "insurance"
    PUC = "puc"
    PERMIT = "permit"
    FITNESS = "fitness"
    ELECTION_COMMISSION = "election_commission"
    VEHICLE_PHOTO_CHASSIS = "vehicle_photo_chassis"
    ADVERTISEMENT_LICENSE = "advertisement_license"


DOCUMENT_TYPES = (
    DocumentType.RC,
    DocumentType.INSURANCE,
    DocumentType.PUC,
    DocumentType.PERMIT,
    DocumentType.FITNESS,
    DocumentType.ELECTION_COMMISSION,
    DocumentType.VEHICLE_PHOTO_CHASSIS,
    DocumentType.ADVERTISEMENT_LICENSE,
)

DOCUMENT_LABELS = {
    DocumentType.RC: "Registration Certificate (RC)",
    DocumentType.INSURANCE: "Vehicle insurance",
    DocumentType.PUC: "Pollution Under Control (PUC)",
    DocumentType.PERMIT: "Vehicle permit",
    DocumentType.FITNESS: "Fitness certificate",
    DocumentType.ELECTION_COMMISSION: "Election Commission approval",
    DocumentType.VEHICLE_PHOTO_CHASSIS: "Vehicle photo & chassis",
    DocumentType.ADVERTISEMENT_LICENSE: "Advertisement license",
}

FINANCE_DOCUMENT_TYPES = (
    DocumentType.INSURANCE,
    DocumentType.ADVERTISEMENT_LICENSE,
)


class DocumentValidity:
    VALID = "valid"
    EXPIRING_30 = "expiring_30"
    EXPIRING_60 = "expiring_60"
    EXPIRED = "expired"


DOCUMENT_VALIDITIES = (
    DocumentValidity.VALID,
    DocumentValidity.EXPIRING_30,
    DocumentValidity.EXPIRING_60,
    DocumentValidity.EXPIRED,
)


class ApprovalStatus:
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


APPROVAL_STATUSES = (
    ApprovalStatus.APPROVED,
    ApprovalStatus.PENDING,
    ApprovalStatus.REJECTED,
)


class AlertType:
    VEHICLE_STARTED = "vehicle_started"
    VEHICLE_STOPPED = "vehicle_stopped"
    LONG_HALT = "long_halt"
    LED_OFF = "led_off"
    KM_EXCEEDED = "km_exceeded"
    GPS_DISCONNECTED = "gps_disconnected"


ALERT_TYPES = (
    AlertType.VEHICLE_STARTED,
    AlertType.VEHICLE_STOPPED,
    AlertType.LONG_HALT,
    AlertType.LED_OFF,
    AlertType.KM_EXCEEDED,
    AlertType.GPS_DISCONNECTED,
)

ALERT_SEVERITY = {
    AlertType.VEHICLE_STARTED: "info",
    AlertType.VEHICLE_STOPPED: "info",
    AlertType.LONG_HALT: "warning",
    AlertType.LED_OFF: "warning",
    AlertType.KM_EXCEEDED: "critical",
    AlertType.GPS_DISCONNECTED: "critical",
}

ALERT_LABELS = {
    AlertType.VEHICLE_STARTED: "Vehicle started",
    AlertType.VEHICLE_STOPPED: "Vehicle stopped",
    AlertType.LONG_HALT: "Long halt detected",
    AlertType.LED_OFF: "LED TV switched off",
    AlertType.KM_EXCEEDED: "Daily km limit exceeded",
    AlertType.GPS_DISCONNECTED: "GPS disconnected",
}

ALERT_KPI_TYPES = (
    AlertType.KM_EXCEEDED,
    AlertType.LONG_HALT,
    AlertType.LED_OFF,
    AlertType.GPS_DISCONNECTED,
    AlertType.VEHICLE_STARTED,
)

UNREAD_ALERT_SEVERITIES = ("warning", "critical")


class ReportKind:
    DAILY = "daily"
    CONSTITUENCY = "constituency"
    VEHICLE = "vehicle"
    ROUTE = "route"
    ALERT = "alert"
    DOCUMENTS = "documents"


REPORT_KINDS = (
    ReportKind.DAILY,
    ReportKind.CONSTITUENCY,
    ReportKind.VEHICLE,
    ReportKind.ROUTE,
    ReportKind.ALERT,
    ReportKind.DOCUMENTS,
)

FINANCE_REPORT_KINDS = (
    ReportKind.DAILY,
    ReportKind.CONSTITUENCY,
    ReportKind.VEHICLE,
    ReportKind.DOCUMENTS,
)

PLATFORM_DEFAULTS = {
    "daily_km_limit": 60,
    "long_halt_minutes": 60,
    "min_stop_minutes": 5,
    "stale_gps_minutes": 15,
    "expire_soon_days": 30,
    "expire_watch_days": 60,
    "approach_ratio": 0.9,
    "operating_start_hour": 8,
    "operating_end_hour": 18,
}

DAILY_KM_LIMIT = PLATFORM_DEFAULTS["daily_km_limit"]
LONG_HALT_MINUTES = PLATFORM_DEFAULTS["long_halt_minutes"]
MIN_STOP_MINUTES = PLATFORM_DEFAULTS["min_stop_minutes"]
STALE_GPS_MINUTES = PLATFORM_DEFAULTS["stale_gps_minutes"]
EXPIRE_SOON_DAYS = PLATFORM_DEFAULTS["expire_soon_days"]
EXPIRE_WATCH_DAYS = PLATFORM_DEFAULTS["expire_watch_days"]
APPROACH_RATIO = PLATFORM_DEFAULTS["approach_ratio"]
OPERATING_START_HOUR = PLATFORM_DEFAULTS["operating_start_hour"]
OPERATING_END_HOUR = PLATFORM_DEFAULTS["operating_end_hour"]
LIVE_SNAPSHOT_MINUTES = 5


def constituency_code(number):
    return f"AC{int(number):02d}"


def district_code(district):
    return DISTRICT_CODES[district]


def format_vehicle_code(district, number, serial):
    return f"GA-{district_code(district)}-{constituency_code(number)}-V{int(serial):02d}"
