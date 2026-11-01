from django.db import connection

from accounts.constants import (
    DEFAULT_MATRIX,
    LEVEL_RANK,
    Level,
    MODULES,
    ROLE_DEFINITIONS,
    RoleCode,
    Scope,
)


def seed_roles_and_permissions():
    table_names = connection.introspection.table_names()
    if "accounts_role" not in table_names or "accounts_rolepermission" not in table_names:
        return

    from accounts.models import Role, RolePermission

    for code, name in ROLE_DEFINITIONS:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": name, "is_system": True},
        )
        matrix = DEFAULT_MATRIX[code]
        for module in MODULES:
            level, scope = matrix[module]
            defaults = {"level": level, "scope": scope}
            if code == RoleCode.SUPER_ADMIN:
                RolePermission.objects.update_or_create(
                    role=role,
                    module=module,
                    defaults=defaults,
                )
            else:
                RolePermission.objects.get_or_create(
                    role=role,
                    module=module,
                    defaults=defaults,
                )


def _role_code(user):
    if getattr(user, "is_superuser", False):
        return RoleCode.SUPER_ADMIN
    role = getattr(user, "role", None)
    return role.code if role else None


def is_super_admin(user):
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and _role_code(user) == RoleCode.SUPER_ADMIN
    )


def _permission_for(user, module):
    role = getattr(user, "role", None)
    if role is None:
        return None
    permissions = getattr(user, "_permission_cache", None)
    if permissions is None:
        permissions = {item.module: item for item in role.permissions.all()}
        user._permission_cache = permissions
    return permissions.get(module)


def user_can(user, module, min_level=Level.VIEW):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if _role_code(user) == RoleCode.SUPER_ADMIN:
        return True
    permission = _permission_for(user, module)
    if permission is None:
        return False
    return LEVEL_RANK.get(permission.level, 0) >= LEVEL_RANK.get(min_level, 0)


def user_scope(user, module):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return Scope.NONE
    if _role_code(user) == RoleCode.SUPER_ADMIN:
        return Scope.ALL
    permission = _permission_for(user, module)
    if permission is None:
        return Scope.NONE
    return permission.scope


def effective_permissions(user):
    if not user or not getattr(user, "role", None):
        return []
    return [
        {
            "module": permission.module,
            "level": permission.level,
            "scope": permission.scope,
        }
        for permission in user.role.permissions.all()
    ]


def assigned_object_ids(user, scope_type):
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return list(
        user.assignments.filter(scope_type=scope_type).values_list("object_id", flat=True)
    )
