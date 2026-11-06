# Live map

Frontend integration guide for the fleet Live Map screen: summary cards, map markers, vehicle table, and CSV export.

The server pulls live GPS from Track360 when credentials are configured, matches devices to vehicles by **IMEI**, updates telemetry, then derives the same statuses used elsewhere (`active`, `long_halt`, `inactive`, `attention`, `exceeded`).

Related docs:

- [Role-based authentication](role-based-authentication.md) — login, JWT, roles, permissions
- [Platform settings](platform-settings.md) — daily km, halt, GPS, and operating-hour thresholds
- [Alerts](alerts.md) — alerts raised from those thresholds
- [History](history.md) — 5-minute GPS snapshots used for routes
- [Vehicle and driver routes](vehicle-driver-routes.md) — vehicle directory and `imei`
- [Constituency routes](constituency-routes.md) — single-constituency `GET /constituencies/{id}/map/`

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| Endpoint | `GET /api/v1/live-map/` |
| Auth | `Authorization: Bearer <access_token>` |
| Permission | `live_map` ≥ `view` |
| CSV export | `export=csv` needs `export_data` ≥ `view`. Finance cannot export |
| Pagination | None |
| GPS feed | Track360 `GET .../auth/pull_api` (cached ~20 seconds) |
| Snapshots | GPS points and alerts are saved at most every 5 minutes |

Poll this endpoint every 15–20 seconds for the live map. Do not poll faster; the Track360 response is cached. Historical points are stored separately every 5 minutes (`python manage.py pull_live_fleet`).

```http
Authorization: Bearer eyJ...
```

## 2. Who can call it

| Role | Live map | CSV | Vehicles shown |
|---|---|---|---|
| Super Admin | yes | yes | All |
| Finance | yes | no | Assigned constituencies only |
| Government Viewer | yes | yes | Assigned constituencies only |
| Constituency Head | yes | yes | Assigned constituencies only |

Unassigned non-admin users get empty `vehicles` and zero counts, not `403`.

## 3. How live GPS is applied

Track360 returns one snapshot per device. Gaadi maps it onto `VehicleTelemetry` when `Vehicle.imei` equals `deviceImei`.

| Track360 field | Live map / telemetry |
|---|---|
| `deviceImei` | Match `vehicle.imei` |
| `latitude`, `longitude` | `lat`, `lng` |
| `speed` | `speed_kmh` (km/h) |
| `ignition` | `ignition` (`"true"` / `"false"` / bool) |
| `status` | `gps_connected` when `online` |
| `lastUpdate` | `last_update` (UTC) |
| `daily_distance` | `today_km` (meters ÷ 1000) |
| `course` | `course` (degrees, not stored) |
| `alarm` | `alarm` (`"null"` becomes `null`) |
| `vehicle_status` | `vehicle_status` (vendor string, e.g. `Dormant`) |

`led_on`, `address` / `location`, and `operating_min` stay as stored on the vehicle. Track360 does not send LED or a street address.

Set IMEI when creating or editing a vehicle:

```json
{ "imei": "864540081600348" }
```

Unmatched Track360 devices are counted in `feed.unmatched` and are **not** shown on the map.

If Track360 is not configured, or `date` is not today, the API uses the last stored telemetry (`source: "stored"`).

## 4. Derived statuses

Same rules as the vehicle directory.

| Status | Meaning | Marker |
|---|---|---|
| `active` | Trip started today and not in a long halt (moving or short stop) | Green |
| `long_halt` | Speed ≤ 2 km/h for ≥ `long_halt_minutes` (default 60) | Amber |
| `inactive` | Trip has not started today | Grey |

Flags:

| Field | Meaning |
|---|---|
| `attention` | Long halt, stale GPS (offline or no update for `stale_gps_minutes`, default 15), or LED off while active |
| `exceeded` | Today's km is greater than `daily_km_limit` (default 60) |

Thresholds come from [Platform settings](platform-settings.md) and are echoed on the live-map payload as `thresholds`.

Trip started is true when Track360 reports ignition on, speed > 2 km/h, or daily distance above 50 m.

## 5. Endpoint

**Title:** Get live map

**Description:** Summary cards, map points, and the vehicle table for the current user's constituencies. Optionally refresh GPS from Track360.

**Endpoint:** `/api/v1/live-map/`

**Type:** `GET`

**Auth:** Bearer token

**Query parameters:**

| Name | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| `constituency` | UUID or `all` | no | `all` | Constituency UUID |
| `status` | string | no | `all` | `all`, `active`, `long_halt`, `inactive`, `attention`, `exceeded` |
| `q` | string | no | `""` | Search vehicle code, registration, driver name |
| `date` | string | no | `today` | `today`, `yesterday`, or `YYYY-MM-DD` |
| `vehicle` | UUID | no | | Highlights one vehicle (`focused_vehicle_id`). Does not hide others |
| `export` | string | no | | `csv` returns a file instead of JSON |

`counts` use the constituency filter only. `q` and `status` filter `vehicles` (map + table) after counts.

**Success response:** `200 OK`

```json
{
  "generated_at": "2026-11-06T11:07:43+00:00",
  "date": "2026-11-06",
  "live": true,
  "source": "stored",
  "feed": {
    "ok": true,
    "provider": "track360",
    "configured": false,
    "live": true,
    "matched": 0,
    "unmatched": 0,
    "error": null
  },
  "focused_vehicle_id": null,
  "thresholds": {
    "daily_km_limit": 60,
    "long_halt_minutes": 60,
    "stale_gps_minutes": 15
  },
  "counts": {
    "total": 4,
    "active": 2,
    "long_halt": 1,
    "inactive": 1,
    "attention": 2,
    "exceeded": 1
  },
  "vehicles": [
    {
      "id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
      "code": "GA-NG-AC01-V01",
      "registration": "GA08AA1001",
      "imei": "864540081600348",
      "constituency": {
        "id": "4c29384c-b039-44c3-8207-ac293eda48db",
        "code": "AC01",
        "name": "Mandrem"
      },
      "driver": {
        "id": "9e88aa01-2222-4bbb-8333-cc44dd55ee66",
        "name": "Ravi Naik"
      },
      "status": "active",
      "attention": false,
      "exceeded": false,
      "today_km": 18.5,
      "daily_km_limit": 60,
      "speed_kmh": 18.5,
      "location": "Mandrem beach road",
      "lat": 15.661,
      "lng": 73.719,
      "ignition": true,
      "led_on": true,
      "gps_connected": true,
      "last_update": "2026-11-06T10:15:00+00:00",
      "operating_min": 95,
      "course": 75.0,
      "device_status": "online",
      "vehicle_status": "Dormant",
      "alarm": null
    }
  ]
}
```

Map `counts` onto the summary cards:

| Card | Field | Caption |
|---|---|---|
| Total vehicles | `counts.total` | In this selection |
| Active | `counts.active` | Moving or short stop |
| Long halt | `counts.long_halt` | Stopped over `thresholds.long_halt_minutes` |
| Inactive | `counts.inactive` | Not started today |
| Attention | `counts.attention` | Halt, LED or GPS issue |
| Exceeded limit | `counts.exceeded` | Above `thresholds.daily_km_limit` km |

Map markers: plot `lat` / `lng`, color by `status`. Skip a vehicle when `lat` or `lng` is `null`.

Table columns:

| Column | Field |
|---|---|
| Vehicle | `code` |
| Registration | `registration` |
| Constituency | `constituency.name` |
| Driver | `driver.name` |
| Status | `status` (`active`, `long_halt`, `inactive`) |
| Today's KM | `today_km` |
| Speed | `speed_kmh` |
| Location | `location` |

CSV (`?export=csv`) columns: `vehicle`, `registration`, `constituency`, `driver`, `status`, `today_km`, `speed_kmh`, `location`.

**Error responses:**

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown status filter." }` | Bad `status` |
| `400` | `{ "detail": "Unknown date." }` | `date` is not `today`, `yesterday`, or `YYYY-MM-DD` |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view live map (or export, for CSV) |
| `429` | `{ "detail": "..." }` | Rate limit |

A Track360 outage does **not** fail the request. `feed.ok` is `false`, `feed.error` has the reason, and `vehicles` still come from stored telemetry.

## 6. Screen mapping

| UI control | Query |
|---|---|
| Constituency dropdown | `constituency=<uuid>` or omit for all |
| Today / Yesterday / date | `date=today`, `date=yesterday`, `date=2026-11-06` |
| Card / chip filter | `status=active` (etc.) |
| Search vehicle | `q=ga-ng-ac01` |
| Open from vehicle profile | `vehicle=<uuid>` — pan/zoom to `focused_vehicle_id` |
| Export CSV | `export=csv` |
| Map vs satellite | Client-only basemap toggle |

## 7. Track360 credentials

Set these in `.env` (never in the client):

```
TRACK360_PULL_URL=https://pullapi-s1.track360.co.in/api/v1/auth/pull_api
TRACK360_USERNAME=
TRACK360_PASSWORD=
TRACK360_TIMEOUT_SECONDS=15
TRACK360_CACHE_SECONDS=20
```

Vendor pull API (server-side only):

```
GET https://pullapi-s1.track360.co.in/api/v1/auth/pull_api?username=...&password=...
Accept: application/json
```

Save a GPS snapshot and raise alerts every 5 minutes (Windows Task Scheduler or cron):

```
python manage.py pull_live_fleet
```

Live Map GET also writes a snapshot if 5 minutes have passed, so a busy map still records history. The scheduled command is required when nobody has the map open.
