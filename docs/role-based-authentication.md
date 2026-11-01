# Role-based authentication

Gaadi uses email/password JWT login. Super Admin creates every other user and can change what each role is allowed to do. Users inherit permissions from their role. There are no per-user permission overrides.

Base URL: `/api/v1/`

The API uses URL path versioning. Only `v1` is accepted. Unversioned paths such as `/api/auth/login/` and unknown versions such as `/api/v2/` return 404.

Send authenticated requests as:

```http
Authorization: Bearer <access_token>
```

Access tokens last 1 hour. Refresh tokens last 7 days.

## 1. Create the first Super Admin

Roles and the default permission matrix are seeded automatically on migrate.

```bash
python manage.py migrate
python manage.py createsuperuser
```

Use an email address when prompted. That account is assigned the `super_admin` role.

Django admin at `/admin/` also works for Super Admin users.

## 2. Log in

`POST /api/v1/auth/login/`

```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

Response includes `access`, `refresh`, and the current user with role, permissions, and assignments.

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "full_name": "Super Admin",
    "role": "super_admin",
    "role_name": "Super Admin",
    "is_active": true,
    "permissions": [
      { "module": "dashboard", "level": "full", "scope": "all" }
    ],
    "assignments": []
  }
}
```

Use the `permissions` list in a client to hide pages the role cannot access.

Refresh an expired access token:

`POST /api/v1/auth/refresh/`

```json
{
  "refresh": "eyJ..."
}
```

Load the current user later:

`GET /api/v1/auth/me/`

## 3. Roles

| Code | Name |
|---|---|
| `super_admin` | Super Admin |
| `finance` | Finance |
| `government_viewer` | Government Viewer |
| `constituency_head` | Constituency Head |

These four roles are system roles. They cannot be deleted.

Each role has one row per module:

- **level:** `none` | `view` | `edit` | `manage` | `full`
- **scope:** `none` | `assigned` | `financial` | `all`

Level rank is `none < view < edit < manage < full`. A user who has `full` can do anything that requires `view`, `edit`, or `manage`.

### Default matrix

| Module | Super Admin | Finance | Government Viewer | Constituency Head |
|---|---|---|---|---|
| `dashboard` | full / all | view / financial | view / all | view / assigned |
| `live_map` | full / all | view / all | view / all | view / assigned |
| `constituencies` | edit / all | view / financial | view / all | view / assigned |
| `vehicles` | edit / all | view / financial | view / all | view / assigned |
| `driver_details` | full / all | none | view / all | view / assigned |
| `vehicle_history` | full / all | none | view / all | view / assigned |
| `alerts` | manage / all | none | view / all | view / assigned |
| `reports` | full / all | view / financial | view / all | view / assigned |
| `compliance_documents` | full / all | view / financial | view / all | view / assigned |
| `document_approvals` | manage / all | none | none | none |
| `financial_records` | full / all | full / all | none | none |
| `user_management` | full / all | none | none | none |
| `role_permissions` | full / all | none | none | none |
| `system_settings` | full / all | none | none | none |
| `records_write` | full / all | edit / financial | none | none |
| `export_data` | full / all | view / financial | view / all | view / assigned |

Super Admin can later change any role except Super Admin. Super Admin stays locked to full access.

## 4. Super Admin: create users

Only Super Admin can call user and role endpoints.

`POST /api/v1/users/`

```json
{
  "email": "head@example.com",
  "password": "HeadPass123!",
  "full_name": "Ward Head",
  "role": "constituency_head",
  "assignments": [
    { "scope_type": "constituency", "object_id": "c-12" },
    { "scope_type": "vehicle", "object_id": "v-9" }
  ]
}
```

`role` must be one of: `super_admin`, `finance`, `government_viewer`, `constituency_head`.

`assignments` are optional. Use them for Constituency Head (and any other role whose scope is `assigned`) so later vehicle/constituency APIs can limit data to those IDs.

Other user endpoints:

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/users/` | List users |
| `GET` | `/api/v1/users/{id}/` | User detail |
| `PATCH` | `/api/v1/users/{id}/` | Update `email`, `full_name`, `role`, `is_active`, optional `password` |
| `DELETE` | `/api/v1/users/{id}/` | Deactivates the user. The row is not deleted. |
| `GET` / `POST` | `/api/v1/users/{id}/assignments/` | List or add assignments |
| `DELETE` | `/api/v1/users/{id}/assignments/{assignment_id}/` | Remove one assignment |

The last remaining Super Admin cannot be deactivated or changed to another role.

## 5. Super Admin: change role permissions

`GET /api/v1/roles/` returns every role and its current matrix.

`PATCH /api/v1/roles/{id}/` updates only the modules you send. Other modules stay as they are.

```json
{
  "permissions": [
    { "module": "live_map", "level": "none", "scope": "none" }
  ]
}
```

Every user on that role gets the new access immediately. Super Admin role updates are rejected.

## 6. Use permissions in new APIs

Check access in views so non-admin roles cannot call APIs they should not see.

```python
from rest_framework.views import APIView

from accounts.constants import Level, Module
from accounts.permissions import HasModuleAccess, HasViewModuleAccess
from accounts.services import assigned_object_ids, user_can, user_scope


class VehicleListView(APIView):
    permission_classes = [HasModuleAccess(Module.VEHICLES, Level.VIEW)]

    def get(self, request):
        scope = user_scope(request.user, Module.VEHICLES)
        if scope == "assigned":
            vehicle_ids = assigned_object_ids(request.user, "vehicle")
            # filter queryset to vehicle_ids
        # scope "financial" or "all" can be handled the same way
```

Or set the module on the view:

```python
class ReportListView(APIView):
    permission_classes = [HasViewModuleAccess]
    permission_module = Module.REPORTS
    permission_min_level = Level.VIEW
```

Helpers:

| Helper | Use |
|---|---|
| `user_can(user, module, min_level)` | True if the user's role meets the level |
| `user_scope(user, module)` | `none`, `assigned`, `financial`, or `all` |
| `assigned_object_ids(user, "constituency")` | IDs assigned to that user |
| `IsSuperAdmin` | Restrict an endpoint to Super Admin |

Super Admin always passes `user_can()` regardless of the stored matrix.

## 7. Typical client flow

1. Super Admin logs in.
2. Super Admin creates Finance, Government Viewer, and Constituency Head users.
3. For Constituency Head, add constituency/vehicle assignments.
4. That user logs in with email and password.
5. The client reads `user.permissions` and shows only allowed screens.
6. Each API still checks `HasModuleAccess` on the server.

## 8. Logging and throttling

API requests under `/api/` are written to the console and to `logs/gaadi.log`. Auth events (login, token refresh, user create/update/deactivate, role permission changes, assignments) are logged without passwords.

Rate limits:

| Scope | Limit | Applies to |
|---|---|---|
| `login` | 5 / minute per IP | `/api/v1/auth/login/` and `/api/v1/auth/refresh/` |
| `anon` | 30 / minute per IP | Unauthenticated API requests |
| `user` | 120 / minute per user | Authenticated API requests |

A throttled request returns `429 Too Many Requests`. Wait and retry, or refresh the access token instead of logging in again.

## 9. Run the auth tests

```bash
python manage.py test accounts
```

