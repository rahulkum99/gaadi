class RoleCode:
    SUPER_ADMIN = "super_admin"
    FINANCE = "finance"
    GOVERNMENT_VIEWER = "government_viewer"
    CONSTITUENCY_HEAD = "constituency_head"


ROLE_DEFINITIONS = (
    (RoleCode.SUPER_ADMIN, "Super Admin"),
    (RoleCode.FINANCE, "Finance"),
    (RoleCode.GOVERNMENT_VIEWER, "Government Viewer"),
    (RoleCode.CONSTITUENCY_HEAD, "Constituency Head"),
)


class Module:
    DASHBOARD = "dashboard"
    LIVE_MAP = "live_map"
    CONSTITUENCIES = "constituencies"
    VEHICLES = "vehicles"
    DRIVER_DETAILS = "driver_details"
    VEHICLE_HISTORY = "vehicle_history"
    ALERTS = "alerts"
    REPORTS = "reports"
    COMPLIANCE_DOCUMENTS = "compliance_documents"
    DOCUMENT_APPROVALS = "document_approvals"
    FINANCIAL_RECORDS = "financial_records"
    USER_MANAGEMENT = "user_management"
    ROLE_PERMISSIONS = "role_permissions"
    SYSTEM_SETTINGS = "system_settings"
    RECORDS_WRITE = "records_write"
    EXPORT_DATA = "export_data"


MODULES = (
    Module.DASHBOARD,
    Module.LIVE_MAP,
    Module.CONSTITUENCIES,
    Module.VEHICLES,
    Module.DRIVER_DETAILS,
    Module.VEHICLE_HISTORY,
    Module.ALERTS,
    Module.REPORTS,
    Module.COMPLIANCE_DOCUMENTS,
    Module.DOCUMENT_APPROVALS,
    Module.FINANCIAL_RECORDS,
    Module.USER_MANAGEMENT,
    Module.ROLE_PERMISSIONS,
    Module.SYSTEM_SETTINGS,
    Module.RECORDS_WRITE,
    Module.EXPORT_DATA,
)


class Level:
    NONE = "none"
    VIEW = "view"
    EDIT = "edit"
    MANAGE = "manage"
    FULL = "full"


LEVELS = (Level.NONE, Level.VIEW, Level.EDIT, Level.MANAGE, Level.FULL)

LEVEL_RANK = {
    Level.NONE: 0,
    Level.VIEW: 1,
    Level.EDIT: 2,
    Level.MANAGE: 3,
    Level.FULL: 4,
}


class Scope:
    NONE = "none"
    ASSIGNED = "assigned"
    FINANCIAL = "financial"
    ALL = "all"


SCOPES = (Scope.NONE, Scope.ASSIGNED, Scope.FINANCIAL, Scope.ALL)


class AssignmentScopeType:
    CONSTITUENCY = "constituency"
    VEHICLE = "vehicle"


ASSIGNMENT_SCOPE_TYPES = (
    AssignmentScopeType.CONSTITUENCY,
    AssignmentScopeType.VEHICLE,
)

NONE = (Level.NONE, Scope.NONE)
VIEW_ALL = (Level.VIEW, Scope.ALL)
VIEW_ASSIGNED = (Level.VIEW, Scope.ASSIGNED)
VIEW_FINANCIAL = (Level.VIEW, Scope.FINANCIAL)
EDIT_ALL = (Level.EDIT, Scope.ALL)
EDIT_FINANCIAL = (Level.EDIT, Scope.FINANCIAL)
MANAGE_ALL = (Level.MANAGE, Scope.ALL)
FULL_ALL = (Level.FULL, Scope.ALL)

DEFAULT_MATRIX = {
    RoleCode.SUPER_ADMIN: {
        Module.DASHBOARD: FULL_ALL,
        Module.LIVE_MAP: FULL_ALL,
        Module.CONSTITUENCIES: EDIT_ALL,
        Module.VEHICLES: EDIT_ALL,
        Module.DRIVER_DETAILS: FULL_ALL,
        Module.VEHICLE_HISTORY: FULL_ALL,
        Module.ALERTS: MANAGE_ALL,
        Module.REPORTS: FULL_ALL,
        Module.COMPLIANCE_DOCUMENTS: FULL_ALL,
        Module.DOCUMENT_APPROVALS: MANAGE_ALL,
        Module.FINANCIAL_RECORDS: FULL_ALL,
        Module.USER_MANAGEMENT: FULL_ALL,
        Module.ROLE_PERMISSIONS: FULL_ALL,
        Module.SYSTEM_SETTINGS: FULL_ALL,
        Module.RECORDS_WRITE: FULL_ALL,
        Module.EXPORT_DATA: FULL_ALL,
    },
    RoleCode.FINANCE: {
        Module.DASHBOARD: VIEW_FINANCIAL,
        Module.LIVE_MAP: VIEW_ALL,
        Module.CONSTITUENCIES: VIEW_FINANCIAL,
        Module.VEHICLES: VIEW_FINANCIAL,
        Module.DRIVER_DETAILS: NONE,
        Module.VEHICLE_HISTORY: NONE,
        Module.ALERTS: NONE,
        Module.REPORTS: VIEW_FINANCIAL,
        Module.COMPLIANCE_DOCUMENTS: VIEW_FINANCIAL,
        Module.DOCUMENT_APPROVALS: NONE,
        Module.FINANCIAL_RECORDS: FULL_ALL,
        Module.USER_MANAGEMENT: NONE,
        Module.ROLE_PERMISSIONS: NONE,
        Module.SYSTEM_SETTINGS: NONE,
        Module.RECORDS_WRITE: EDIT_FINANCIAL,
        Module.EXPORT_DATA: VIEW_FINANCIAL,
    },
    RoleCode.GOVERNMENT_VIEWER: {
        Module.DASHBOARD: VIEW_ALL,
        Module.LIVE_MAP: VIEW_ALL,
        Module.CONSTITUENCIES: VIEW_ALL,
        Module.VEHICLES: VIEW_ALL,
        Module.DRIVER_DETAILS: VIEW_ALL,
        Module.VEHICLE_HISTORY: VIEW_ALL,
        Module.ALERTS: VIEW_ALL,
        Module.REPORTS: VIEW_ALL,
        Module.COMPLIANCE_DOCUMENTS: VIEW_ALL,
        Module.DOCUMENT_APPROVALS: NONE,
        Module.FINANCIAL_RECORDS: NONE,
        Module.USER_MANAGEMENT: NONE,
        Module.ROLE_PERMISSIONS: NONE,
        Module.SYSTEM_SETTINGS: NONE,
        Module.RECORDS_WRITE: NONE,
        Module.EXPORT_DATA: VIEW_ALL,
    },
    RoleCode.CONSTITUENCY_HEAD: {
        Module.DASHBOARD: VIEW_ASSIGNED,
        Module.LIVE_MAP: VIEW_ASSIGNED,
        Module.CONSTITUENCIES: VIEW_ASSIGNED,
        Module.VEHICLES: VIEW_ASSIGNED,
        Module.DRIVER_DETAILS: VIEW_ASSIGNED,
        Module.VEHICLE_HISTORY: VIEW_ASSIGNED,
        Module.ALERTS: VIEW_ASSIGNED,
        Module.REPORTS: VIEW_ASSIGNED,
        Module.COMPLIANCE_DOCUMENTS: VIEW_ASSIGNED,
        Module.DOCUMENT_APPROVALS: NONE,
        Module.FINANCIAL_RECORDS: NONE,
        Module.USER_MANAGEMENT: NONE,
        Module.ROLE_PERMISSIONS: NONE,
        Module.SYSTEM_SETTINGS: NONE,
        Module.RECORDS_WRITE: NONE,
        Module.EXPORT_DATA: VIEW_ASSIGNED,
    },
}
