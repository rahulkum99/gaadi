# Platform settings

Frontend integration guide for the Super Admin **Platform settings** screen (fleet limits, GPS & halts, compliance windows, operating hours).

These values drive Live Map statuses, Alerts, History stop detection, and document-expiry reports. Changing them does not rewrite old GPS points; new snapshots and alerts use the saved values immediately.

Related docs:

- [Live map](live-map.md)
- [Alerts](alerts.md)
- [History](history.md)
- [Reports](reports.md)
- [Role-based authentication](role-based-authentication.md)

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| Read / save | `GET` / `PUT` / `PATCH` `/api/v1/settings/` |
| Reset | `POST /api/v1/settings/reset/` |
| Auth | `Authorization: Bearer <access_token>` |
| Permission | `system_settings` ≥ `view` to read, ≥ `edit` to save or reset |
| Roles | Super Admin only (other roles receive `403`) |

There is a single settings row for the whole platform. `GET` creates it with defaults if it does not exist yet.

Live GPS is stored at most every **5 minutes**. That interval is not editable on this screen; it is returned as read-only `live_snapshot_minutes`.

## 2. Fields (matches the settings form)

| Form group | Field | JSON | Default | Rules |
|---|---|---|---|---|
| Fleet limits | Daily km limit | `daily_km_limit` | `60` | > 0. Triggers `km_exceeded` when today's trip distance goes over this value |
| GPS & halts | Long halt threshold (minutes) | `long_halt_minutes` | `60` | ≥ `min_stop_minutes`. Minutes stopped before a vehicle is treated as on a long halt |
| GPS & halts | Minimum stop duration (minutes) | `min_stop_minutes` | `5` | ≥ 1. Stops shorter than this are ignored when building trip summaries |
| GPS & halts | Stale GPS threshold (minutes) | `stale_gps_minutes` | `15` | ≥ 1. Minutes without a fresh GPS fix before a disconnected alert is raised |
| Compliance | Expiring soon (days) | `expire_soon_days` | `30` | ≥ 1. Documents within this many days of expiry are marked expiring soon |
| Compliance | Expiring watch (days) | `expire_watch_days` | `60` | Must be **greater than** expiring soon |
| Compliance | Approach ratio | `approach_ratio` | `0.9` | 0–1. Fraction of a document validity period used for early warning |
| Operating hours | Start hour (0–23) | `operating_start_hour` | `8` | Start of the nominal operating day in 24-hour local time |
| Operating hours | End hour (0–23) | `operating_end_hour` | `18` | Must be **after** the start hour |

Read-only extras on `GET`:

| Field | Meaning |
|---|---|
| `live_snapshot_minutes` | Always `5`. How often live GPS is persisted |
| `defaults` | Factory defaults for **Reset to defaults** |
| `updated_at` | Last save time |
| `updated_by` | Name or email of the Super Admin who saved, or `null` |

## 3. Endpoints

### Get settings

**Endpoint:** `GET /api/v1/settings/`

**Type:** `GET`

**Auth:** Bearer token, `system_settings` ≥ `view`

```json
{
  "daily_km_limit": 60,
  "long_halt_minutes": 60,
  "min_stop_minutes": 5,
  "stale_gps_minutes": 15,
  "expire_soon_days": 30,
  "expire_watch_days": 60,
  "approach_ratio": 0.9,
  "operating_start_hour": 8,
  "operating_end_hour": 18,
  "live_snapshot_minutes": 5,
  "updated_at": "2026-11-06T11:30:00+00:00",
  "updated_by": "Super Admin",
  "defaults": {
    "daily_km_limit": 60,
    "long_halt_minutes": 60,
    "min_stop_minutes": 5,
    "stale_gps_minutes": 15,
    "expire_soon_days": 30,
    "expire_watch_days": 60,
    "approach_ratio": 0.9,
    "operating_start_hour": 8,
    "operating_end_hour": 18
  }
}
```

Map the JSON 1:1 onto the form. Show helper text from the table above. **Reset to defaults** can copy `defaults` into the form, then call save or the reset endpoint.

### Save changes

**Endpoint:** `PUT /api/v1/settings/` or `PATCH /api/v1/settings/`

**Type:** `PUT` (full form) / `PATCH` (partial)

**Auth:** Bearer token, `system_settings` ≥ `edit`

Send the same field names as the GET body (without `live_snapshot_minutes`, `defaults`, `updated_at`, `updated_by`).

Success: `200 OK` with the same shape as GET.

### Reset to defaults

**Endpoint:** `POST /api/v1/settings/reset/`

**Type:** `POST`

**Auth:** Bearer token, `system_settings` ≥ `edit`

No body. Restores every editable field to `defaults` and returns the GET payload.

## 4. Errors

| Status | Body | When |
|---|---|---|
| `400` | Field errors, e.g. `{ "expire_watch_days": ["Must be greater than expiring soon, used for the wider watch window."] }` | Validation failed |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view or edit system settings |
| `429` | `{ "detail": "..." }` | Rate limit |

## 5. Screen mapping

| UI control | API |
|---|---|
| Load the page | `GET /api/v1/settings/` |
| Save changes | `PUT /api/v1/settings/` with the form values |
| Reset to defaults | `POST /api/v1/settings/reset/` |

Hide this page unless `user.permissions` includes `system_settings` at `view` or higher. Only Super Admin has that module by default.
