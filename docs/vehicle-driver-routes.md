# Vehicle and driver routes

Frontend integration guide for vehicle APIs and the nested driver fields. Use this file when building the vehicle directory, vehicle detail, driver card, live map handoff, alerts, and document tabs.

There is **no** `/drivers/` resource. Create and edit a driver by sending `driver_*` fields on the vehicle create and update calls. Every vehicle has exactly one driver.

Related docs:

- [Role-based authentication](role-based-authentication.md) — login, JWT, roles, permissions
- [Constituency routes](constituency-routes.md) — constituency list, map, and `GET /constituencies/{id}/vehicles/`
- [Live map](live-map.md) — fleet live map fed by Track360 GPS
- [Constituency, vehicle, and compliance](constituency-vehicle-compliance.md) — fleet overview

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| Versioning | URL path. Only `v1` is accepted |
| Auth | `Authorization: Bearer <access_token>` |
| Content type | `application/json` for JSON bodies. Use `multipart/form-data` when uploading photos or document files |
| Pagination | None. List endpoints return a JSON array |
| IDs | UUID strings |
| Vehicle codes | Auto-generated as `GA-NG-AC01-V01` (state–district–constituency–serial) |
| Registration | Stored uppercase. The server trims and uppercases on write |

Every request needs a valid access token. Tokens last 1 hour by default. Refresh with `POST /api/v1/auth/refresh/`.

```http
Authorization: Bearer eyJ...
```

Authenticated users are limited to 120 requests per minute. A throttled call returns `429 Too Many Requests`.

## 2. Who can call what

| Endpoint | Required module | Required level |
|---|---|---|
| `GET /vehicles/` | `vehicles` | `view` |
| `POST /vehicles/` | `vehicles` | `edit` |
| `GET /vehicles/{id}/` | `vehicles` | `view` |
| `PATCH /vehicles/{id}/` | `vehicles` | `edit` |
| `GET /vehicles/{id}/alerts/` | `alerts` | `view` |
| `GET /vehicles/{id}/documents/` | `compliance_documents` | `view` |
| `PUT /vehicles/{id}/documents/{type}/` | `compliance_documents` | `edit` |
| `POST /vehicles/{id}/documents/{type}/review/` | `document_approvals` | `manage` |

Default role matrix:

| Role | List / detail | Create / edit | Driver phone & licence | Alerts | Documents | Approve / reject |
|---|---|---|---|---|---|---|
| Super Admin | yes | yes | yes | yes | all 8 types | yes |
| Finance | yes | no | no | no | `insurance`, `advertisement_license` only | no |
| Government Viewer | yes | no | yes | yes | all 8 types | no |
| Constituency Head | yes | no | yes | yes | all 8 types | no |

Driver contact is shown only when the user has `driver_details` ≥ `view` **and** is not Finance. Finance always gets `driver.contact_restricted: true` with `phone`, `licence_number`, and `licence_expiry` set to `null`.

Read `user.permissions` from login or `GET /api/v1/auth/me/` and hide screens the role cannot open. The server still enforces the same rules.

## 3. Assignment scope

Super Admin sees every vehicle.

Finance, Government Viewer, and Constituency Head only see vehicles whose constituency Super Admin assigned to them.

If Super Admin assigns nothing:

- `GET /vehicles/` returns `[]`
- detail, alerts, and document URLs return `404` with `{ "detail": "Not found." }`

Treat unassigned IDs the same as missing IDs. Do not show a separate "forbidden" state.

## 4. Derived vehicle status

Vehicle `status` comes from the latest telemetry snapshot. It is not stored.

| Status | Meaning | UI suggestion |
|---|---|---|
| `active` | Trip started and not in a long halt | Green |
| `long_halt` | Speed ≤ 2 km/h for ≥ 60 minutes | Amber |
| `inactive` | Trip has not started today | Grey |

Flags on every vehicle row:

| Field | Meaning |
|---|---|
| `attention` | Long halt, stale GPS (disconnected or no update for 15 minutes), or LED off while active |
| `exceeded` | Today's km is greater than 60 |
| `today_km` | Distance today, one decimal |
| `daily_km_limit` | Always `60` |
| `operating_min` | Minutes operated today |

List filter `status` values (query param, not the same set as vehicle `status`):

| Filter | Matches |
|---|---|
| `all` | Everything |
| `active` | `status == "active"` |
| `long_halt` | `status == "long_halt"` |
| `inactive` | `status == "inactive"` |
| `attention` | `attention == true` |
| `exceeded` | `exceeded == true` |

## 5. Shared objects

### 5.1 Driver object

Returned inside every vehicle row and vehicle detail. There is no separate driver list.

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Driver primary key |
| `name` | string | Always present |
| `photo` | string (URL) \| null | Absolute URL when present |
| `phone` | string \| null | `null` when contact is restricted |
| `licence_number` | string \| null | `null` when contact is restricted |
| `licence_expiry` | string (YYYY-MM-DD) \| null | `null` when restricted or not set |
| `duty_status` | `"on_duty"` \| `"off_duty"` | Default on create is `off_duty` |
| `contact_restricted` | boolean | `true` for Finance (and anyone without `driver_details` view) |

```json
{
  "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
  "name": "Ravi Naik",
  "photo": null,
  "phone": "9876543210",
  "licence_number": "GA0120230001",
  "licence_expiry": "2027-03-31",
  "duty_status": "on_duty",
  "contact_restricted": false
}
```

Finance example:

```json
{
  "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
  "name": "Ravi Naik",
  "photo": null,
  "phone": null,
  "licence_number": null,
  "licence_expiry": null,
  "duty_status": "on_duty",
  "contact_restricted": true
}
```

When `contact_restricted` is `true`, show the name only. Do not render empty phone or licence fields as "missing".

### 5.2 Vehicle row

Returned by list, constituency vehicles, and as the base of vehicle detail.

```json
{
  "id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
  "code": "GA-NG-AC01-V01",
  "registration": "GA08AA1001",
  "photo": "https://api.example.com/media/vehicles/.../photo.jpg",
  "plate_photo": null,
  "led_photo": null,
  "chassis_photo": null,
  "constituency": {
    "id": "4c29384c-b039-44c3-8207-ac293eda48db",
    "code": "AC01",
    "number": 1,
    "name": "Mandrem",
    "district": "north_goa",
    "district_label": "North Goa",
    "lat": 15.663,
    "lng": 73.721,
    "image": null
  },
  "driver": {
    "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
    "name": "Ravi Naik",
    "photo": null,
    "phone": "9876543210",
    "licence_number": "GA0120230001",
    "licence_expiry": "2027-03-31",
    "duty_status": "on_duty",
    "contact_restricted": false
  },
  "telemetry": {
    "lat": 15.661,
    "lng": 73.719,
    "address": "Mandrem depot",
    "speed_kmh": 20.0,
    "ignition": true,
    "led_on": true,
    "gps_connected": true,
    "last_update": "2026-11-04T10:15:00+00:00",
    "trip_started": true
  },
  "status": "active",
  "attention": false,
  "exceeded": false,
  "today_km": 18.0,
  "daily_km_limit": 60,
  "operating_min": 95
}
```

Photo fields are absolute URLs or `null`: `photo`, `plate_photo`, `led_photo`, `chassis_photo`.

### 5.3 Vehicle detail extras

Create, get, and patch return the vehicle row plus:

| Field | Type | Notes |
|---|---|---|
| `documents` | array | All allowed document types, including empty rows |
| `alerts` | array | Derived alerts for this vehicle |
| `quick_actions` | object | Client routes, not API paths |

```json
{
  "quick_actions": {
    "live_map": "/live-map?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
    "history": "/history?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
    "share": null,
    "notifications": "/alerts?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55"
  }
}
```

Use `quick_actions` as in-app routes. `share` is `null` — copy the current page URL on the client.

### 5.4 Alert

```json
{
  "id": "GA-NG-AC01-V02-long_halt",
  "type": "long_halt",
  "severity": "warning",
  "vehicle_id": "8b2d3c01-3333-4ccc-8444-dd55ee66ff77",
  "vehicle_code": "GA-NG-AC01-V02",
  "constituency_id": "4c29384c-b039-44c3-8207-ac293eda48db",
  "created_at": "2026-11-04T08:45:00+00:00",
  "description": "Long halt detected",
  "lat": 15.66,
  "lng": 73.72
}
```

| `type` | `severity` | Description |
|---|---|---|
| `km_exceeded` | `critical` | Today's distance is over 60 km |
| `gps_disconnected` | `critical` | GPS off or no update for 15 minutes |
| `long_halt` | `warning` | Speed ≤ 2 km/h for ≥ 60 minutes |
| `led_off` | `warning` | LED off while the vehicle is on duty |

`id` is `{vehicle_code}-{type}`, not a database row. Alerts disappear when telemetry returns to normal. `created_at` is telemetry `last_update` and can be `null`.

### 5.5 Document

| Field | Type | Notes |
|---|---|---|
| `type` | string | One of the eight types below |
| `label` | string | Human label |
| `file` | string (URL) \| null | Absolute URL when uploaded |
| `file_name` | string | Empty string when none |
| `start_date` | string (YYYY-MM-DD) \| null | |
| `end_date` | string (YYYY-MM-DD) \| null | |
| `approval` | `"approved"` \| `"pending"` \| `"rejected"` \| null | `null` until a file/dates are saved |
| `review_comment` | string | Empty until reviewed |
| `reviewed_at` | string (ISO datetime) \| null | |
| `reviewed_by` | string \| null | Reviewer full name or email |
| `validity` | `"valid"` \| `"expiring_30"` \| `"expiring_60"` \| `"expired"` | Derived from `end_date` |

Document types:

| `type` | `label` |
|---|---|
| `rc` | Registration Certificate (RC) |
| `insurance` | Vehicle insurance |
| `puc` | Pollution Under Control (PUC) |
| `permit` | Vehicle permit |
| `fitness` | Fitness certificate |
| `election_commission` | Election Commission approval |
| `vehicle_photo_chassis` | Vehicle photo & chassis |
| `advertisement_license` | Advertisement license |

Validity:

| Status | Meaning |
|---|---|
| `valid` | No end date, or more than 60 days left |
| `expiring_60` | Ends in 31–60 days |
| `expiring_30` | Ends within 30 days |
| `expired` | End date is in the past |

```json
{
  "type": "insurance",
  "label": "Vehicle insurance",
  "file": "https://api.example.com/media/vehicles/.../insurance.pdf",
  "file_name": "insurance.pdf",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "approval": "pending",
  "review_comment": "",
  "reviewed_at": null,
  "reviewed_by": null,
  "validity": "valid"
}
```

## 6. How drivers work

| Action | What happens |
|---|---|
| `POST /vehicles/` | Creates a **new** driver, then attaches it to the new vehicle |
| `PATCH /vehicles/{id}/` | Updates the **existing** driver. Does not create a second driver |
| Reassign constituency | Driver stays on the same vehicle |
| Driver photo | Stored on the model, but create/update do **not** accept a driver photo field |

Write fields (flat on the vehicle body, not nested):

| Write field | Maps to `driver.*` | Create | Update |
|---|---|---|---|
| `driver_name` | `name` | required | optional |
| `driver_phone` | `phone` | optional | optional |
| `driver_licence_number` | `licence_number` | optional | optional |
| `driver_licence_expiry` | `licence_expiry` | optional (`YYYY-MM-DD` or `null`) | optional |
| `driver_duty_status` | `duty_status` | optional, default `off_duty` | optional |

There is no endpoint to list all drivers, delete a driver, or move a driver to another vehicle.

## 7. Endpoint index

| # | Title | Type | Endpoint |
|---|---|---|---|
| 1 | List vehicles | `GET` | `/api/v1/vehicles/` |
| 2 | Create vehicle and driver | `POST` | `/api/v1/vehicles/` |
| 3 | Get vehicle and driver detail | `GET` | `/api/v1/vehicles/{id}/` |
| 4 | Update vehicle, driver, or telemetry | `PATCH` | `/api/v1/vehicles/{id}/` |
| 5 | List vehicle alerts | `GET` | `/api/v1/vehicles/{id}/alerts/` |
| 6 | List vehicle documents | `GET` | `/api/v1/vehicles/{id}/documents/` |
| 7 | Upload or replace a document | `PUT` | `/api/v1/vehicles/{id}/documents/{type}/` |
| 8 | Approve or reject a document | `POST` | `/api/v1/vehicles/{id}/documents/{type}/review/` |

There is no `PUT` or `DELETE` for vehicles, and no `/drivers/` routes.

`{id}` is the vehicle UUID. `{type}` is a document type string such as `insurance`.

Related (documented in [constituency-routes.md](constituency-routes.md)):

| Type | Endpoint | Notes |
|---|---|---|
| `GET` | `/api/v1/constituencies/{constituency_id}/vehicles/` | Vehicles in one constituency. No search/filter |

---

## 8. Endpoints

### 8.1 List vehicles

**Title:** List vehicles

**Description:** Returns every vehicle the current user can see, with driver, constituency, telemetry, and derived flags. Use this for the vehicle directory. Documents, alerts, and quick actions are omitted.

**Endpoint:** `/api/v1/vehicles/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `vehicles` ≥ `view`

**Query parameters:**

| Name | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| `q` | string | no | `""` | Search against vehicle `code`, `registration`, and driver `name` (case-insensitive) |
| `constituency` | UUID or `all` | no | `all` | Constituency UUID. `all` or empty = no constituency filter |
| `status` | string | no | `all` | `all`, `active`, `attention`, `inactive`, `exceeded`, `long_halt` |

**Body:** none

**Success response:** `200 OK` — array of [vehicle rows](#52-vehicle-row)

```json
[
  {
    "id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
    "code": "GA-NG-AC01-V01",
    "registration": "GA08AA1001",
    "photo": null,
    "plate_photo": null,
    "led_photo": null,
    "chassis_photo": null,
    "constituency": {
      "id": "4c29384c-b039-44c3-8207-ac293eda48db",
      "code": "AC01",
      "number": 1,
      "name": "Mandrem",
      "district": "north_goa",
      "district_label": "North Goa",
      "lat": 15.663,
      "lng": 73.721,
      "image": null
    },
    "driver": {
      "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
      "name": "Ravi Naik",
      "photo": null,
      "phone": "9876543210",
      "licence_number": "GA0120230001",
      "licence_expiry": "2027-03-31",
      "duty_status": "on_duty",
      "contact_restricted": false
    },
    "telemetry": {
      "lat": 15.661,
      "lng": 73.719,
      "address": "Mandrem depot",
      "speed_kmh": 20.0,
      "ignition": true,
      "led_on": true,
      "gps_connected": true,
      "last_update": "2026-11-04T10:15:00+00:00",
      "trip_started": true
    },
    "status": "active",
    "attention": false,
    "exceeded": false,
    "today_km": 18.0,
    "daily_km_limit": 60,
    "operating_min": 95
  }
]
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown status filter." }` | `status` is not `all` or a known filter |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view vehicles |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Debounce `q`. Searching `"ravi"` matches driver name.
- Empty array means no assignments or no matches, not an error.
- There is no `count` wrapper and no pages.
- Filter chips should use the filter `status` values (`attention`, `exceeded`), not only `active` / `inactive`.

---

### 8.2 Create vehicle and driver

**Title:** Create vehicle and driver

**Description:** Creates a vehicle, a new driver, empty telemetry, and eight empty document slots. Super Admin only under the default matrix. The server assigns `code` from constituency district, constituency number, and the next serial (`V01`–`V99`).

**Endpoint:** `/api/v1/vehicles/`

**Type:** `POST`

**Auth:** Bearer token

**Permission:** `vehicles` ≥ `edit`

**Query parameters:** none

**Body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `constituency` | UUID | yes | Must be a real constituency |
| `registration` | string | yes | Max 32. Trimmed and uppercased. Must be unique |
| `imei` | string | no | Track360 `deviceImei`. Unique when set. Used by live map GPS overlay |
| `driver_name` | string | yes | Max 128 |
| `driver_phone` | string | no | Max 32. Blank allowed |
| `driver_licence_number` | string | no | Max 64. Blank allowed |
| `driver_licence_expiry` | date \| null | no | `YYYY-MM-DD` |
| `driver_duty_status` | string | no | `on_duty` or `off_duty`. Default `off_duty` |
| `photo` | file | no | Vehicle photo. Multipart |
| `plate_photo` | file | no | Multipart |
| `led_photo` | file | no | Multipart |
| `chassis_photo` | file | no | Multipart |

JSON example:

```json
{
  "constituency": "4c29384c-b039-44c3-8207-ac293eda48db",
  "registration": "ga08zz9999",
  "driver_name": "New Driver",
  "driver_phone": "9898989898",
  "driver_licence_number": "GA0120260099",
  "driver_licence_expiry": "2028-06-30",
  "driver_duty_status": "on_duty"
}
```

The stored registration becomes `GA08ZZ9999`.

Multipart example (when uploading photos):

```http
POST /api/v1/vehicles/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

constituency=4c29384c-b039-44c3-8207-ac293eda48db
registration=GA08ZZ9999
driver_name=New Driver
driver_phone=9898989898
driver_duty_status=on_duty
photo=<file>
plate_photo=<file>
```

**Success response:** `201 Created` — [vehicle detail](#53-vehicle-detail-extras)

A new vehicle starts `inactive` until telemetry has `trip_started: true`. `documents` has eight rows (two for Finance). `alerts` is usually `[]`.

```json
{
  "id": "c0ffee00-aaaa-4bbb-8ccc-ddddeeeeffff",
  "code": "GA-NG-AC01-V03",
  "registration": "GA08ZZ9999",
  "photo": null,
  "plate_photo": null,
  "led_photo": null,
  "chassis_photo": null,
  "constituency": {
    "id": "4c29384c-b039-44c3-8207-ac293eda48db",
    "code": "AC01",
    "number": 1,
    "name": "Mandrem",
    "district": "north_goa",
    "district_label": "North Goa",
    "lat": 15.663,
    "lng": 73.721,
    "image": null
  },
  "driver": {
    "id": "11111111-2222-4333-8444-555555555555",
    "name": "New Driver",
    "photo": null,
    "phone": "9898989898",
    "licence_number": "GA0120260099",
    "licence_expiry": "2028-06-30",
    "duty_status": "on_duty",
    "contact_restricted": false
  },
  "telemetry": {
    "lat": null,
    "lng": null,
    "address": "",
    "speed_kmh": 0,
    "ignition": false,
    "led_on": false,
    "gps_connected": false,
    "last_update": null,
    "trip_started": false
  },
  "status": "inactive",
  "attention": true,
  "exceeded": false,
  "today_km": 0.0,
  "daily_km_limit": 60,
  "operating_min": 0,
  "documents": [],
  "alerts": [],
  "quick_actions": {
    "live_map": "/live-map?vehicle=c0ffee00-aaaa-4bbb-8ccc-ddddeeeeffff",
    "history": "/history?vehicle=c0ffee00-aaaa-4bbb-8ccc-ddddeeeeffff",
    "share": null,
    "notifications": "/alerts?vehicle=c0ffee00-aaaa-4bbb-8ccc-ddddeeeeffff"
  }
}
```

`documents` in a real `201` is an array of eight document objects (empty files). Truncated above.

A new vehicle with no GPS update is `inactive` and `attention: true` because GPS is treated as stale.

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "constituency": ["Unknown constituency."] }` | Bad constituency UUID |
| `400` | `{ "registration": ["Registration already exists."] }` | Duplicate plate |
| `400` | `{ "driver_name": ["This field is required."] }` | Missing driver name |
| `400` | `{ "driver_duty_status": ["Unknown duty status."] }` | Not `on_duty` or `off_duty` |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot create vehicles |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Do not send `code`. The server generates it.
- Do not nest driver as `{ "driver": { "name": "..." } }`. Use the flat `driver_*` keys.
- After create, route to vehicle detail using the returned `id`.
- Photos require `multipart/form-data`. Do not JSON-encode files.

---

### 8.3 Get vehicle and driver detail

**Title:** Get vehicle and driver detail

**Description:** Returns one vehicle with driver, telemetry, documents, alerts, and quick-action routes. Use this for the vehicle profile page.

**Endpoint:** `/api/v1/vehicles/{id}/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `vehicles` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK` — [vehicle row](#52-vehicle-row) plus `documents`, `alerts`, and `quick_actions`

```json
{
  "id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
  "code": "GA-NG-AC01-V01",
  "registration": "GA08AA1001",
  "photo": null,
  "plate_photo": null,
  "led_photo": null,
  "chassis_photo": null,
  "constituency": { "id": "4c29384c-b039-44c3-8207-ac293eda48db", "code": "AC01", "number": 1, "name": "Mandrem", "district": "north_goa", "district_label": "North Goa", "lat": 15.663, "lng": 73.721, "image": null },
  "driver": {
    "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
    "name": "Ravi Naik",
    "photo": null,
    "phone": "9876543210",
    "licence_number": "GA0120230001",
    "licence_expiry": "2027-03-31",
    "duty_status": "on_duty",
    "contact_restricted": false
  },
  "telemetry": {
    "lat": 15.661,
    "lng": 73.719,
    "address": "Mandrem depot",
    "speed_kmh": 20.0,
    "ignition": true,
    "led_on": true,
    "gps_connected": true,
    "last_update": "2026-11-04T10:15:00+00:00",
    "trip_started": true
  },
  "status": "active",
  "attention": false,
  "exceeded": false,
  "today_km": 18.0,
  "daily_km_limit": 60,
  "operating_min": 95,
  "documents": [
    {
      "type": "rc",
      "label": "Registration Certificate (RC)",
      "file": null,
      "file_name": "",
      "start_date": null,
      "end_date": null,
      "approval": null,
      "review_comment": "",
      "reviewed_at": null,
      "reviewed_by": null,
      "validity": "valid"
    }
  ],
  "alerts": [],
  "quick_actions": {
    "live_map": "/live-map?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
    "history": "/history?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
    "share": null,
    "notifications": "/alerts?vehicle=7a1c2b90-1111-4aaa-8222-bb33cc44dd55"
  }
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view vehicles |
| `404` | `{ "detail": "Not found." }` | Unknown UUID or vehicle not in an assigned constituency |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Prefer this call for the profile page. You get driver, documents, and alerts together.
- Finance receives only insurance and advertisement-license documents, and redacted driver contact.
- `quick_actions.history` is a client route. There is no vehicle-history API on this module yet.

---

### 8.4 Update vehicle, driver, or telemetry

**Title:** Update vehicle, driver, or telemetry

**Description:** Partial update. Change assignment, registration, photos, driver fields, and/or the telemetry snapshot. Driver fields update the existing driver. Telemetry is nested as `telemetry`.

**Endpoint:** `/api/v1/vehicles/{id}/`

**Type:** `PATCH`

**Auth:** Bearer token

**Permission:** `vehicles` ≥ `edit`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |

**Query parameters:** none

**Body:** any subset of:

| Field | Type | Notes |
|---|---|---|
| `constituency` | UUID | Reassign. Must exist |
| `registration` | string | Unique, uppercased |
| `imei` | string \| null | Track360 device IMEI. Blank clears it |
| `driver_name` | string | |
| `driver_phone` | string | Blank allowed |
| `driver_licence_number` | string | Blank allowed |
| `driver_licence_expiry` | date \| null | |
| `driver_duty_status` | `"on_duty"` \| `"off_duty"` | |
| `photo` | file | Multipart |
| `plate_photo` | file | Multipart |
| `led_photo` | file | Multipart |
| `chassis_photo` | file | Multipart |
| `telemetry` | object | See below |

`telemetry` fields (all optional inside the object):

| Field | Type | Notes |
|---|---|---|
| `lat` | number \| null | |
| `lng` | number \| null | |
| `address` | string | |
| `speed_kmh` | number | |
| `ignition` | boolean | |
| `led_on` | boolean | |
| `gps_connected` | boolean | |
| `last_update` | datetime | ISO 8601 |
| `trip_started` | boolean | `true` is required for `active` / `long_halt` |
| `today_km` | number | Compared to 60 for `exceeded` |
| `operating_min` | integer | |

Driver-only patch:

```json
{
  "driver_name": "Ravi Naik",
  "driver_phone": "9876543210",
  "driver_duty_status": "on_duty"
}
```

Telemetry snapshot:

```json
{
  "telemetry": {
    "lat": 15.661,
    "lng": 73.719,
    "address": "Mandrem depot",
    "speed_kmh": 18,
    "ignition": true,
    "led_on": true,
    "gps_connected": true,
    "last_update": "2026-11-04T10:15:00Z",
    "trip_started": true,
    "today_km": 22.5,
    "operating_min": 110
  }
}
```

Reassign constituency:

```json
{
  "constituency": "8f1d2c0a-1111-4aaa-8222-bb33cc44dd55"
}
```

Changing constituency does **not** regenerate `code`. The original `GA-NG-AC01-V01` style code stays.

**Success response:** `200 OK` — same shape as get detail

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "constituency": ["Unknown constituency."] }` | Bad constituency |
| `400` | `{ "registration": ["Registration already exists."] }` | Duplicate plate |
| `400` | `{ "driver_duty_status": ["Unknown duty status."] }` | Invalid duty status |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot edit vehicles |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Send only changed fields.
- Photos need `multipart/form-data`. Telemetry is easier as JSON; do not mix file uploads and nested `telemetry` JSON unless your client can send both (JSON `telemetry` will not parse as multipart nested object unless you flatten keys — prefer two requests, or JSON without files).
- There is no endpoint to clear an existing photo.
- After a telemetry patch, re-read `status`, `attention`, `exceeded`, and `alerts` from the response.

---

### 8.5 List vehicle alerts

**Title:** List vehicle alerts

**Description:** Returns today's derived alerts for one vehicle. Use this for the alerts tab or notification drawer when you already have the vehicle ID.

**Endpoint:** `/api/v1/vehicles/{id}/alerts/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `alerts` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK` — array of [alerts](#54-alert)

```json
[
  {
    "id": "GA-NG-AC01-V02-long_halt",
    "type": "long_halt",
    "severity": "warning",
    "vehicle_id": "8b2d3c01-3333-4ccc-8444-dd55ee66ff77",
    "vehicle_code": "GA-NG-AC01-V02",
    "constituency_id": "4c29384c-b039-44c3-8207-ac293eda48db",
    "created_at": "2026-11-04T08:45:00+00:00",
    "description": "Long halt detected",
    "lat": 15.66,
    "lng": 73.72
  }
]
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view alerts (Finance by default) |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Same objects as `alerts` on vehicle detail. Call this if the tab loads separately.
- Empty array means no current issues.
- Hide this tab when the user lacks `alerts` view.

---

### 8.6 List vehicle documents

**Title:** List vehicle documents

**Description:** Returns every document type for the vehicle, including types with no file yet. Creates missing slots on first read. Finance only sees insurance and advertisement license.

**Endpoint:** `/api/v1/vehicles/{id}/documents/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `compliance_documents` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK` — array of [documents](#55-document)

Always eight items for non-finance users, in this order: `rc`, `insurance`, `puc`, `permit`, `fitness`, `election_commission`, `vehicle_photo_chassis`, `advertisement_license`.

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view compliance documents |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Render a card per item even when `file` is `null` (missing upload).
- Color by `validity` and `approval`.
- Vehicle detail already includes `documents`. Use this call to refresh the documents tab after upload/review.

---

### 8.7 Upload or replace a document

**Title:** Upload or replace a document

**Description:** Writes file and/or dates for one document type. Sets `approval` to `pending` and clears the previous review.

**Endpoint:** `/api/v1/vehicles/{id}/documents/{type}/`

**Type:** `PUT`

**Auth:** Bearer token

**Permission:** `compliance_documents` ≥ `edit`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |
| `type` | string | yes | One of the eight document types |

**Query parameters:** none

**Body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | no | Multipart |
| `file_name` | string | no | Defaults to the uploaded file name |
| `start_date` | date \| null | no | `YYYY-MM-DD` |
| `end_date` | date \| null | no | `YYYY-MM-DD` |

```http
PUT /api/v1/vehicles/{id}/documents/insurance/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<file>
file_name=insurance-2026.pdf
start_date=2026-01-01
end_date=2026-12-31
```

JSON without a file (dates only):

```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-12-31"
}
```

**Success response:** `200 OK` — one [document](#55-document)

```json
{
  "type": "insurance",
  "label": "Vehicle insurance",
  "file": "https://api.example.com/media/vehicles/.../insurance-2026.pdf",
  "file_name": "insurance-2026.pdf",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "approval": "pending",
  "review_comment": "",
  "reviewed_at": null,
  "reviewed_by": null,
  "validity": "valid"
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown document type." }` | `{type}` is not one of the eight types |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot edit documents |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned vehicle |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Any successful PUT resets approval to `pending`. Re-upload after rejection to send it back for review.
- Default matrix: only Super Admin has `compliance_documents` edit.
- After success, replace that card in the documents list with the response.

---

### 8.8 Approve or reject a document

**Title:** Approve or reject a document

**Description:** Records a review decision. Default matrix: Super Admin only (`document_approvals` ≥ `manage`).

**Endpoint:** `/api/v1/vehicles/{id}/documents/{type}/review/`

**Type:** `POST`

**Auth:** Bearer token

**Permission:** `document_approvals` ≥ `manage`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Vehicle ID |
| `type` | string | yes | Document type |

**Query parameters:** none

**Body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `decision` | string | yes | `approved` or `rejected` |
| `comment` | string | no | Blank allowed |

```json
{
  "decision": "approved",
  "comment": "Looks good"
}
```

Reject:

```json
{
  "decision": "rejected",
  "comment": "Dates do not match the certificate"
}
```

**Success response:** `200 OK` — one [document](#55-document) with `approval`, `review_comment`, `reviewed_at`, and `reviewed_by` filled

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown document type." }` | Unknown `{type}` |
| `400` | `{ "decision": ["Decision must be approved or rejected."] }` | `pending` or any other value |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot approve documents |
| `404` | `{ "detail": "Not found." }` | Unknown vehicle, unassigned vehicle, or that document slot does not exist |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Hide approve/reject unless the user has `document_approvals` ≥ `manage`.
- `decision` cannot be `pending`. Pending is set automatically on upload.
- Constituency Head and Finance get `403` on this call by default.

---

## 9. Typical screen mapping

| Screen | Call |
|---|---|
| Vehicle directory | `GET /vehicles/?q=&constituency=&status=` |
| Vehicle profile | `GET /vehicles/{id}/` |
| Create vehicle + driver (admin) | `POST /vehicles/` |
| Edit vehicle / driver | `GET /vehicles/{id}/` then `PATCH /vehicles/{id}/` |
| Driver card on profile | `driver` object from detail. Hide phone/licence when `contact_restricted` |
| Live map screen | `GET /live-map/` — [live-map.md](live-map.md) |
| Live map from vehicle | Client route `quick_actions.live_map`, then `GET /live-map/?vehicle={id}` |
| Alerts tab | `alerts` from detail, or `GET /vehicles/{id}/alerts/` |
| Documents tab | `documents` from detail, or `GET /vehicles/{id}/documents/` |
| Upload document | `PUT /vehicles/{id}/documents/{type}/` |
| Approve / reject | `POST /vehicles/{id}/documents/{type}/review/` |
| Vehicles inside a constituency | `GET /constituencies/{id}/vehicles/` |

Suggested client flow:

1. Log in. Store `access`, `refresh`, and `user.permissions`.
2. If the user has `vehicles` ≥ `view`, open the directory.
3. Call `GET /vehicles/`. Render `code`, `registration`, `driver.name`, `status`, `attention`, `today_km`.
4. On row click, route to `/vehicles/{id}` and call detail.
5. Hide Create / Edit unless `vehicles` ≥ `edit`.
6. Hide driver phone and licence when `driver.contact_restricted` is `true`.
7. Hide Alerts unless `alerts` ≥ `view`.
8. Hide document upload unless `compliance_documents` ≥ `edit`.
9. Hide approve/reject unless `document_approvals` ≥ `manage`.

## 10. Common errors

Handle these on every vehicle call:

| HTTP | Shape | Client action |
|---|---|---|
| `400` | `{ "detail": "..." }` or field errors | Show the message next to the field or as a toast |
| `401` | `{ "detail": "..." }` | Refresh the access token, or send the user to login |
| `403` | `{ "detail": "..." }` | Hide the screen. The role cannot use this module |
| `404` | `{ "detail": "Not found." }` | Show not found. The vehicle is missing or not assigned |
| `429` | `{ "detail": "..." }` | Wait and retry |

Field errors on create / patch look like:

```json
{
  "registration": ["Registration already exists."],
  "driver_name": ["This field is required."],
  "constituency": ["Unknown constituency."]
}
```

## 11. Media

Photo and document `file` values are absolute URLs when a file exists, otherwise `null`.

When `AWS_STORAGE_BUCKET_NAME` is set, files live in S3 under `media/` and URLs may be signed. Without a bucket, files are served from `/media/` in debug mode.

Render `null` as a placeholder.

## 12. Seed data

In development:

```bash
python manage.py seed_fleet
```

That attaches a small demo fleet (drivers and telemetry) onto constituencies Super Admin has already created with `POST /api/v1/constituencies/`. It does not create constituencies.
