from rest_framework.permissions import BasePermission

from accounts.constants import Level, Module
from accounts.services import is_super_admin, user_can


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_super_admin(request.user)


def HasModuleAccess(module, min_level=Level.VIEW):
    class _HasModuleAccess(BasePermission):
        def has_permission(self, request, view):
            return user_can(request.user, module, min_level)

    return _HasModuleAccess


class HasViewModuleAccess(BasePermission):
    """Use with `permission_module` and optional `permission_min_level` on the view."""

    def has_permission(self, request, view):
        module = getattr(view, "permission_module", Module.DASHBOARD)
        min_level = getattr(view, "permission_min_level", Level.VIEW)
        return user_can(request.user, module, min_level)
