# Constituency routes

Frontend integration guide for constituency APIs. Use this file when building list, detail, map, alert, and report screens.

Related docs:

- [Role-based authentication](role-based-authentication.md) — login, JWT, roles, permissions
- [Live map](live-map.md) — fleet-wide live map
- [Constituency, vehicle, and compliance](constituency-vehicle-compliance.md) — fleet overview

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| Versioning | URL path. Only `v1` is accepted |
| Auth | `Authorization: Bearer <access_token>` |
| Content type | `application/json` for JSON bodies. Use `multipart/form-data` when uploading `image` |
| Pagination | None. List endpoints return a JSON array |
| IDs | UUID strings |
| Codes | Auto-generated as `AC01`, `AC02`, … from `number` |

Every request needs a valid access token. Tokens last 1 hour by default. Refresh with `POST /api/v1/auth/refresh/`.

```http
Authorization: Bearer eyJ...
```

Authenticated users are limited to 120 requests per minute. A throttled call returns `429 Too Many Requests`.

## 2. Who can call what

Module for list, create, detail, edit, and map: `constituencies`.

| Endpoint | Required module | Required level |
|---|---|---|
| `GET /constituencies/` | `constituencies` | `view` |
| `POST /constituencies/` | `constituencies` | `edit` |
| `GET /constituencies/{id}/` | `constituencies` | `view` |
| `PATCH /constituencies/{id}/` | `constituencies` | `edit` |
| `GET /constituencies/{id}/vehicles/` | `vehicles` | `view` |
| `GET /constituencies/{id}/map/` | `constituencies` | `view` |
| `GET /constituencies/{id}/alerts/` | `alerts` | `view` |
| `GET /constituencies/{id}/report/` | `reports` | `view` |

Default role matrix:

| Role | List / detail / map | Create / edit | Vehicles | Alerts | Report |
|---|---|---|---|---|---|
| Super Admin | yes | yes | yes | yes | yes |
| Finance | yes | no | yes | no | yes |
| Government Viewer | yes | no | yes | yes | yes |
| Constituency Head | yes | no | yes | yes | yes |

Finance has no `alerts` access, so `GET .../alerts/` returns `403`. Hide that tab for finance users.

Read `user.permissions` from login or `GET /api/v1/auth/me/` and hide screens the role cannot open. The server still enforces the same rules.

## 3. Assignment scope

Super Admin sees every constituency.

Finance, Government Viewer, and Constituency Head only see constituencies Super Admin assigned to them. Role does not expand the set.

If Super Admin assigns nothing:

- list endpoints return `[]`
- detail, vehicles, map, alerts, and report return `404` with `{ "detail": "Not found." }`

Treat unassigned IDs the same as missing IDs. Do not show a separate "forbidden" state.

Assign constituencies with the user APIs (Super Admin only):

```http
PUT /api/v1/users/{user_uuid}/assignments/
```

```json
{
  "assignments": [
    { "scope_type": "constituency", "object_id": "<mandrem-uuid>" },
    { "scope_type": "constituency", "object_id": "<panaji-uuid>" }
  ]
}
```

## 4. Derived statuses

Constituency `status` is computed from assigned vehicles. It is not stored.

| Status | Meaning | UI suggestion |
|---|---|---|
| `operational` | At least one vehicle is not inactive, and none need attention or exceeded today's km | Green |
| `needs_attention` | Any assigned vehicle needs attention or exceeded today's 60 km limit | Amber / red |
| `inactive` | No vehicles, or every vehicle is inactive | Grey |

Vehicle `status` comes from the latest telemetry snapshot:

| Status | Meaning |
|---|---|
| `active` | Trip started and not in a long halt |
| `long_halt` | Speed ≤ 2 km/h for ≥ 60 minutes |
| `inactive` | Trip has not started today |

Vehicle flags:

| Field | Meaning |
|---|---|
| `attention` | Long halt, stale GPS (disconnected or no update for 15 minutes), or LED off while active |
| `exceeded` | Today's km is greater than 60 |

## 5. Shared objects

Reuse these shapes across screens. Field names below match the API exactly.

### 5.1 Constituency list item

Returned by list, create, and patch. Create and patch omit `vehicles`. List also omits `vehicles`.

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Primary key |
| `code` | string | `AC01` style. Server-generated from `number` |
| `number` | integer | Unique assembly number |
| `name` | string | Display name |
| `district` | `"north_goa"` \| `"south_goa"` | Use this in forms |
| `district_label` | `"North Goa"` \| `"South Goa"` | Use this on cards |
| `lat` | number \| null | Constituency map pin |
| `lng` | number \| null | Constituency map pin |
| `image` | string (URL) \| null | Absolute URL when present |
| `total` | integer | Assigned vehicle count |
| `active` | integer | Vehicles with `status=active` |
| `inactive` | integer | Vehicles with `status=inactive` |
| `attention` | integer | Vehicles with `attention=true` |
| `exceeded` | integer | Vehicles with `exceeded=true` |
| `today_km` | number | Sum of vehicle `today_km`, one decimal |
| `status` | `"operational"` \| `"needs_attention"` \| `"inactive"` | Derived |

### 5.2 Vehicle row

Returned inside constituency detail and by `.../vehicles/`. Finance users get redacted driver contact.

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

If `driver.contact_restricted` is `true` (Finance), `phone` and `licence_number` are `null`. Show the driver name only.

`duty_status` is `"on_duty"` or `"off_duty"`.

### 5.3 Alert

Derived from current telemetry. IDs are stable for the current snapshot (`{vehicle_code}-{type}`), not database rows.

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

`created_at` is the telemetry `last_update`. It can be `null`.

## 6. Endpoint index

| # | Title | Type | Endpoint |
|---|---|---|---|
| 1 | List constituencies | `GET` | `/api/v1/constituencies/` |
| 2 | Create constituency | `POST` | `/api/v1/constituencies/` |
| 3 | Get constituency detail | `GET` | `/api/v1/constituencies/{id}/` |
| 4 | Update constituency | `PATCH` | `/api/v1/constituencies/{id}/` |
| 5 | List constituency vehicles | `GET` | `/api/v1/constituencies/{id}/vehicles/` |
| 6 | Get constituency map points | `GET` | `/api/v1/constituencies/{id}/map/` |
| 7 | List constituency alerts | `GET` | `/api/v1/constituencies/{id}/alerts/` |
| 8 | Get constituency report | `GET` | `/api/v1/constituencies/{id}/report/` |

There is no `PUT` or `DELETE` for constituencies.

`{id}` is the constituency UUID.

---

## 7. Endpoints

### 7.1 List constituencies

**Title:** List constituencies

**Description:** Returns every constituency the current user can see, with rollup counts and derived status. Use this for the constituency directory, cards, and filters. Vehicle arrays are omitted to keep the payload small.

**Endpoint:** `/api/v1/constituencies/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `constituencies` ≥ `view`

**Query parameters:**

| Name | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| `q` | string | no | `""` | Search against `name`, `code`, and `number` (case-insensitive) |
| `status` | string | no | `all` | `all`, `operational`, `needs_attention`, `inactive` |
| `ordering` | string | no | `code` | `code`, `name`, `-code`, `-name` |

`ordering=code` sorts by assembly `number`, not the string `AC01`. Prefix `-` for descending.

**Body:** none

**Success response:** `200 OK` — array of [constituency list items](#51-constituency-list-item)

```json
[
  {
    "id": "4c29384c-b039-44c3-8207-ac293eda48db",
    "code": "AC01",
    "number": 1,
    "name": "Mandrem",
    "district": "north_goa",
    "district_label": "North Goa",
    "lat": 15.663,
    "lng": 73.721,
    "image": null,
    "total": 2,
    "active": 1,
    "inactive": 0,
    "attention": 1,
    "exceeded": 0,
    "today_km": 30.0,
    "status": "needs_attention"
  },
  {
    "id": "8f1d2c0a-1111-4aaa-8222-bb33cc44dd55",
    "code": "AC11",
    "number": 11,
    "name": "Panaji",
    "district": "north_goa",
    "district_label": "North Goa",
    "lat": 15.491,
    "lng": 73.828,
    "image": null,
    "total": 1,
    "active": 0,
    "inactive": 1,
    "attention": 0,
    "exceeded": 0,
    "today_km": 0.0,
    "status": "inactive"
  }
]
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown status filter." }` | `status` is not `all` or a known constituency status |
| `400` | `{ "detail": "Unknown ordering." }` | `ordering` is not `code` or `name` (with optional `-`) |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view constituencies |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Debounce `q` on the search box. Empty `q` returns the full scoped list.
- Empty array means the user has no assignments, not an error.
- There is no `count` wrapper and no `next` / `previous` pages.

---

### 7.2 Create constituency

**Title:** Create constituency

**Description:** Creates a constituency. Super Admin only under the default matrix. The server assigns `number` (next available) and `code` (`AC{number}`) when `number` is omitted.

**Endpoint:** `/api/v1/constituencies/`

**Type:** `POST`

**Auth:** Bearer token

**Permission:** `constituencies` ≥ `edit`

**Query parameters:** none

**Body (JSON):**

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Max 128 characters |
| `district` | string | yes | `north_goa` or `south_goa` |
| `number` | integer | no | Unique. Auto-increments if omitted |
| `lat` | number | no | Map pin |
| `lng` | number | no | Map pin |
| `image` | file | no | Send as multipart, not JSON |

JSON example:

```json
{
  "name": "New Ward",
  "district": "north_goa",
  "lat": 15.5,
  "lng": 73.9
}
```

Multipart example (when uploading an image):

```http
POST /api/v1/constituencies/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

name=New Ward
district=north_goa
lat=15.5
lng=73.9
image=<file>
```

**Success response:** `201 Created` — [constituency list item](#51-constituency-list-item)

```json
{
  "id": "c0ffee00-aaaa-4bbb-8ccc-ddddeeeeffff",
  "code": "AC01",
  "number": 1,
  "name": "New Ward",
  "district": "north_goa",
  "district_label": "North Goa",
  "lat": 15.5,
  "lng": 73.9,
  "image": null,
  "total": 0,
  "active": 0,
  "inactive": 0,
  "attention": 0,
  "exceeded": 0,
  "today_km": 0.0,
  "status": "inactive"
}
```

A new constituency with no vehicles is always `inactive`.

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "name": ["This field is required."] }` | Missing required field |
| `400` | `{ "district": ["Unknown district."] }` | District is not `north_goa` or `south_goa` |
| `400` | `{ "number": ["..."] }` | Duplicate or invalid number |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot create constituencies |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Do not send `code`. The server generates it from `number`.
- After create, append the returned object to the list or refetch `GET /constituencies/`.
- Super Admin must add every constituency with this endpoint. The server does not pre-load the 40 Goa seats.

---

### 7.3 Get constituency detail

**Title:** Get constituency detail

**Description:** Returns one constituency with the same rollup fields as the list, plus the full vehicle rows and today's derived alerts. Use this for the constituency overview page.

**Endpoint:** `/api/v1/constituencies/{id}/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `constituencies` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK`

Same fields as the list item, plus:

| Field | Type | Notes |
|---|---|---|
| `vehicles` | array of [vehicle rows](#52-vehicle-row) | All vehicles in this constituency |
| `alerts` | array of [alerts](#53-alert) | Flattened from every vehicle |

```json
{
  "id": "4c29384c-b039-44c3-8207-ac293eda48db",
  "code": "AC01",
  "number": 1,
  "name": "Mandrem",
  "district": "north_goa",
  "district_label": "North Goa",
  "lat": 15.663,
  "lng": 73.721,
  "image": "https://api.example.com/media/constituencies/.../ward.jpg",
  "total": 2,
  "active": 1,
  "inactive": 0,
  "attention": 1,
  "exceeded": 0,
  "today_km": 30.0,
  "status": "needs_attention",
  "vehicles": [
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
        "image": "https://api.example.com/media/constituencies/.../ward.jpg"
      },
      "driver": {
        "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
        "name": "Ravi Naik",
        "photo": null,
        "phone": "9876543210",
        "licence_number": null,
        "licence_expiry": null,
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
  ],
  "alerts": [
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
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view constituencies |
| `404` | `{ "detail": "Not found." }` | Unknown UUID or not assigned to this user |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Prefer this call for the overview page. You get counts, vehicles, and alerts in one response.
- `GET .../vehicles/` and `GET .../alerts/` are available if you want those tabs to load separately.
- `alerts` is always present. Empty array means no current issues.

---

### 7.4 Update constituency

**Title:** Update constituency

**Description:** Partial update of name, district, number, coordinates, or image. Changing `number` also regenerates `code`.

**Endpoint:** `/api/v1/constituencies/{id}/`

**Type:** `PATCH`

**Auth:** Bearer token

**Permission:** `constituencies` ≥ `edit`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

**Body:** any subset of the create fields. All fields are optional.

```json
{
  "name": "Mandrem West",
  "lat": 15.664,
  "lng": 73.722
}
```

To replace the image, send `multipart/form-data` with the `image` file and any other fields you want to change.

**Success response:** `200 OK` — [constituency list item](#51-constituency-list-item) (no `vehicles`, no `alerts`)

```json
{
  "id": "4c29384c-b039-44c3-8207-ac293eda48db",
  "code": "AC01",
  "number": 1,
  "name": "Mandrem West",
  "district": "north_goa",
  "district_label": "North Goa",
  "lat": 15.664,
  "lng": 73.722,
  "image": "https://api.example.com/media/constituencies/.../ward.jpg",
  "total": 2,
  "active": 1,
  "inactive": 0,
  "attention": 1,
  "exceeded": 0,
  "today_km": 30.0,
  "status": "needs_attention"
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "district": ["Unknown district."] }` | Invalid district |
| `400` | `{ "number": ["..."] }` | Duplicate number |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot edit constituencies |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Send only changed fields.
- If the user changes `number`, update any local labels that show `code`.
- There is no endpoint to clear an existing image.

---

### 7.5 List constituency vehicles

**Title:** List constituency vehicles

**Description:** Returns every vehicle assigned to the constituency, with driver, telemetry, and derived flags. Use this for the vehicles tab when you do not need the constituency rollup.

**Endpoint:** `/api/v1/constituencies/{id}/vehicles/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `vehicles` ≥ `view`

The user must also be allowed to see this constituency. Unassigned IDs still return `404`.

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

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
      "licence_number": null,
      "licence_expiry": null,
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
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view vehicles |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- This list is not filtered. Filter locally by `status`, `attention`, or `exceeded` if the tab needs chips.
- For the global vehicle directory with search, use `GET /api/v1/vehicles/?constituency={id}` instead.
- Vehicle codes look like `GA-NG-AC01-V01` (state-district-constituency-serial).

---

### 7.6 Get constituency map points

**Title:** Get constituency map points

**Description:** Compact payload for a live map. Includes the constituency pin and one point per vehicle with current lat/lng and status.

**Endpoint:** `/api/v1/constituencies/{id}/map/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `constituencies` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK`

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Constituency ID |
| `code` | string | `AC01` |
| `name` | string | Display name |
| `lat` | number \| null | Constituency center |
| `lng` | number \| null | Constituency center |
| `vehicles` | array | Map markers |

Each `vehicles[]` item:

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Vehicle ID |
| `code` | string | Vehicle code |
| `registration` | string | Plate |
| `status` | `"active"` \| `"long_halt"` \| `"inactive"` | Marker color |
| `attention` | boolean | Extra badge |
| `lat` | number \| null | Latest telemetry |
| `lng` | number \| null | Latest telemetry |
| `address` | string | Latest address, may be `""` |

```json
{
  "id": "4c29384c-b039-44c3-8207-ac293eda48db",
  "code": "AC01",
  "name": "Mandrem",
  "lat": 15.663,
  "lng": 73.721,
  "vehicles": [
    {
      "id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
      "code": "GA-NG-AC01-V01",
      "registration": "GA08AA1001",
      "status": "active",
      "attention": false,
      "lat": 15.661,
      "lng": 73.719,
      "address": "Mandrem depot"
    },
    {
      "id": "8b2d3c01-3333-4ccc-8444-dd55ee66ff77",
      "code": "GA-NG-AC01-V02",
      "registration": "GA08AA1002",
      "status": "long_halt",
      "attention": true,
      "lat": 15.66,
      "lng": 73.72,
      "address": "Mandrem depot"
    }
  ]
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view constituencies |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- Skip a vehicle marker when `lat` or `lng` is `null`.
- If the constituency pin is `null`, fit the map to vehicle points only.
- Poll this endpoint for live updates. There is no websocket.
- Suggested marker colors: `active` green, `long_halt` amber, `inactive` grey. Show a warning badge when `attention` is `true`.

---

### 7.7 List constituency alerts

**Title:** List constituency alerts

**Description:** Returns today's derived alerts for every vehicle in the constituency. Use this for the alerts tab or a notification drawer.

**Endpoint:** `/api/v1/constituencies/{id}/alerts/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `alerts` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK` — array of [alerts](#53-alert)

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
  },
  {
    "id": "GA-SG-AC31-V01-km_exceeded",
    "type": "km_exceeded",
    "severity": "critical",
    "vehicle_id": "aa11bb22-4444-4ddd-8555-ee66ff778899",
    "vehicle_code": "GA-SG-AC31-V01",
    "constituency_id": "11111111-2222-4333-8444-555555555555",
    "created_at": "2026-11-04T09:10:00+00:00",
    "description": "60 km daily limit exceeded. Today's distance is 72.4 km.",
    "lat": 15.274,
    "lng": 73.958
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

- Alerts are computed, not stored. They disappear when telemetry returns to normal.
- Group by `severity` (`critical` first) or by `type`.
- `id` is `{vehicle_code}-{type}`. A vehicle can appear more than once if it has several alert types.
- Click-through: `/alerts?vehicle={vehicle_id}` or the vehicle detail page.

---

### 7.8 Get constituency report

**Title:** Get constituency report

**Description:** Compact summary for a report card or print view. Counts only — no vehicle rows.

**Endpoint:** `/api/v1/constituencies/{id}/report/`

**Type:** `GET`

**Auth:** Bearer token

**Permission:** `reports` ≥ `view`

**Path parameters:**

| Name | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID | yes | Constituency ID |

**Query parameters:** none

**Body:** none

**Success response:** `200 OK`

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Constituency ID |
| `code` | string | `AC01` |
| `name` | string | Display name |
| `status` | `"operational"` \| `"needs_attention"` \| `"inactive"` | Derived |
| `vehicles` | integer | Same as list `total` |
| `active` | integer | Active vehicles |
| `inactive` | integer | Inactive vehicles |
| `attention` | integer | Vehicles needing attention |
| `exceeded` | integer | Vehicles over 60 km today |
| `today_km` | number | Sum of today's km |
| `alerts` | integer | Number of derived alerts, not an array |

```json
{
  "id": "4c29384c-b039-44c3-8207-ac293eda48db",
  "code": "AC01",
  "name": "Mandrem",
  "status": "needs_attention",
  "vehicles": 2,
  "active": 1,
  "inactive": 0,
  "attention": 1,
  "exceeded": 0,
  "today_km": 30.0,
  "alerts": 1
}
```

**Error responses:**

| Status | Body | When |
|---|---|---|
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view reports |
| `404` | `{ "detail": "Not found." }` | Unknown or unassigned ID |
| `429` | `{ "detail": "..." }` | Rate limit |

**Frontend notes:**

- `vehicles` here is a count. On the detail endpoint, `vehicles` is an array and the count is `total`.
- `alerts` here is a count. On the detail endpoint, `alerts` is an array.
- There is no CSV export on this route. Document CSV lives at `GET /api/v1/reports/documents/?export=csv`.

---

## 8. Typical screen mapping

| Screen | Call |
|---|---|
| Constituency directory | `GET /constituencies/?q=&status=&ordering=name` |
| Constituency overview | `GET /constituencies/{id}/` |
| Edit constituency form | `GET /constituencies/{id}/` then `PATCH /constituencies/{id}/` |
| Create constituency (admin) | `POST /constituencies/` |
| Vehicles tab | `GET /constituencies/{id}/vehicles/` or `vehicles` from detail |
| Live map | `GET /constituencies/{id}/map/` on an interval |
| Alerts tab | `GET /constituencies/{id}/alerts/` or `alerts` from detail |
| Report card | `GET /constituencies/{id}/report/` |

Suggested client flow:

1. Log in. Store `access`, `refresh`, and `user.permissions`.
2. If the user has `constituencies` ≥ `view`, open the directory.
3. Call `GET /constituencies/`. Render cards from `code`, `name`, `image`, `status`, `total`, `active`, `attention`.
4. On card click, route to `/constituencies/{id}` and call detail.
5. Hide Create / Edit unless `constituencies` ≥ `edit`.
6. Hide Alerts unless `alerts` ≥ `view`.
7. Hide Report unless `reports` ≥ `view`.

## 9. Common errors

Handle these on every constituency call:

| HTTP | Shape | Client action |
|---|---|---|
| `400` | `{ "detail": "..." }` or field errors | Show the message next to the field or as a toast |
| `401` | `{ "detail": "..." }` | Refresh the access token, or send the user to login |
| `403` | `{ "detail": "..." }` | Hide the screen. The role cannot use this module |
| `404` | `{ "detail": "Not found." }` | Show not found. The constituency is missing or not assigned |
| `429` | `{ "detail": "..." }` | Wait and retry. Do not log in again if the token is still valid |

Field errors on create / patch look like:

```json
{
  "name": ["This field is required."],
  "district": ["Unknown district."]
}
```

## 10. Media

`image` is an absolute URL when a file exists, otherwise `null`.

When `AWS_STORAGE_BUCKET_NAME` is set, files live in S3 under `media/` and URLs may be signed. Without a bucket, files are served from `/media/` in debug mode.

Render `null` as a placeholder. Do not request `/media/` yourself unless the API returned that URL.

## 11. Seed data

Super Admin adds constituencies with `POST /api/v1/constituencies/`. After at least one exists, development can attach a small demo fleet:

```bash
python manage.py seed_fleet
```

That command does **not** create constituencies. If none exist, it prints a warning and exits.
