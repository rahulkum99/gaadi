from accounts.constants import AssignmentScopeType
from accounts.services import assigned_object_ids, is_super_admin
from fleet.models import Constituency, Vehicle


def assigned_constituency_ids(user):
    return [str(item) for item in assigned_object_ids(user, AssignmentScopeType.CONSTITUENCY)]


def scoped_constituencies(user):
    queryset = Constituency.objects.all()
    if is_super_admin(user):
        return queryset
    ids = assigned_constituency_ids(user)
    if not ids:
        return queryset.none()
    return queryset.filter(id__in=ids)


def scoped_vehicles(user):
    queryset = Vehicle.objects.select_related(
        "constituency",
        "driver",
        "telemetry",
    ).prefetch_related("documents")
    if is_super_admin(user):
        return queryset
    ids = assigned_constituency_ids(user)
    if not ids:
        return queryset.none()
    return queryset.filter(constituency_id__in=ids)


def can_access_constituency(user, constituency_id):
    if is_super_admin(user):
        return True
    return str(constituency_id) in assigned_constituency_ids(user)


def can_access_vehicle(user, vehicle):
    if is_super_admin(user):
        return True
    return str(vehicle.constituency_id) in assigned_constituency_ids(user)
