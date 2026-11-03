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
    KM_EXCEEDED = "km_exceeded"
    LONG_HALT = "long_halt"
    LED_OFF = "led_off"
    GPS_DISCONNECTED = "gps_disconnected"


ALERT_TYPES = (
    AlertType.KM_EXCEEDED,
    AlertType.LONG_HALT,
    AlertType.LED_OFF,
    AlertType.GPS_DISCONNECTED,
)

ALERT_SEVERITY = {
    AlertType.KM_EXCEEDED: "critical",
    AlertType.GPS_DISCONNECTED: "critical",
    AlertType.LONG_HALT: "warning",
    AlertType.LED_OFF: "warning",
}

ALERT_LABELS = {
    AlertType.KM_EXCEEDED: "60 km daily limit exceeded",
    AlertType.GPS_DISCONNECTED: "GPS disconnected",
    AlertType.LONG_HALT: "Long halt detected",
    AlertType.LED_OFF: "LED TV switched off",
}

DAILY_KM_LIMIT = 60
LONG_HALT_MINUTES = 60
STALE_GPS_MINUTES = 15
EXPIRE_SOON_DAYS = 30
EXPIRE_WATCH_DAYS = 60

GOA_CONSTITUENCIES = (
    (1, "Mandrem", District.NORTH_GOA, 15.663, 73.721),
    (2, "Pernem", District.NORTH_GOA, 15.717, 73.797),
    (3, "Bicholim", District.NORTH_GOA, 15.6, 73.949),
    (4, "Tivim", District.NORTH_GOA, 15.598, 73.853),
    (5, "Mapusa", District.NORTH_GOA, 15.591, 73.808),
    (6, "Siolim", District.NORTH_GOA, 15.623, 73.768),
    (7, "Saligao", District.NORTH_GOA, 15.548, 73.789),
    (8, "Calangute", District.NORTH_GOA, 15.544, 73.755),
    (9, "Porvorim", District.NORTH_GOA, 15.532, 73.831),
    (10, "Aldona", District.NORTH_GOA, 15.591, 73.874),
    (11, "Panaji", District.NORTH_GOA, 15.491, 73.828),
    (12, "Taleigao", District.NORTH_GOA, 15.473, 73.821),
    (13, "Santa Cruz", District.NORTH_GOA, 15.478, 73.858),
    (14, "St. Andre", District.NORTH_GOA, 15.502, 73.908),
    (15, "Cumbarjua", District.NORTH_GOA, 15.522, 73.951),
    (16, "Maem", District.NORTH_GOA, 15.548, 73.982),
    (17, "Sanquelim", District.NORTH_GOA, 15.564, 74.008),
    (18, "Poriem", District.NORTH_GOA, 15.618, 74.048),
    (19, "Valpoi", District.NORTH_GOA, 15.532, 74.137),
    (20, "Priol", District.NORTH_GOA, 15.448, 74.018),
    (21, "Ponda", District.NORTH_GOA, 15.403, 74.015),
    (22, "Siroda", District.NORTH_GOA, 15.361, 74.021),
    (23, "Marcaim", District.NORTH_GOA, 15.421, 73.981),
    (24, "Mormugao", District.SOUTH_GOA, 15.409, 73.791),
    (25, "Vasco Da Gama", District.SOUTH_GOA, 15.398, 73.811),
    (26, "Dabolim", District.SOUTH_GOA, 15.381, 73.848),
    (27, "Cortalim", District.SOUTH_GOA, 15.372, 73.908),
    (28, "Nuvem", District.SOUTH_GOA, 15.318, 73.941),
    (29, "Curtorim", District.SOUTH_GOA, 15.282, 74.021),
    (30, "Fatorda", District.SOUTH_GOA, 15.289, 73.971),
    (31, "Margao", District.SOUTH_GOA, 15.274, 73.958),
    (32, "Benaulim", District.SOUTH_GOA, 15.258, 73.928),
    (33, "Navelim", District.SOUTH_GOA, 15.251, 73.981),
    (34, "Cuncolim", District.SOUTH_GOA, 15.178, 73.994),
    (35, "Velim", District.SOUTH_GOA, 15.162, 73.968),
    (36, "Quepem", District.SOUTH_GOA, 15.213, 74.071),
    (37, "Curchorem", District.SOUTH_GOA, 15.264, 74.108),
    (38, "Sanvordem", District.SOUTH_GOA, 15.269, 74.131),
    (39, "Sanguem", District.SOUTH_GOA, 15.229, 74.151),
    (40, "Canacona", District.SOUTH_GOA, 15.018, 74.021),
)


def constituency_code(number):
    return f"AC{int(number):02d}"


def district_code(district):
    return DISTRICT_CODES[district]


def format_vehicle_code(district, number, serial):
    return f"GA-{district_code(district)}-{constituency_code(number)}-V{int(serial):02d}"
