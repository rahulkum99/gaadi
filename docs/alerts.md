# Alerts

Frontend integration guide for `/alerts` and `/alerts/:id`: list, KPIs, bell, and alert detail.

Alerts are evaluated from live telemetry using [platform settings](platform-settings.md) (daily km cap, long-halt minutes, stale GPS, minimum stop). They are persisted when live GPS is saved (every 5 minutes, or on Live Map poll once that interval has passed). Opening a detail page is enough for the client to mark an item read; the server does not store read state.

Related docs:

- [Platform settings](platform-settings.md)
- [Live map](live-map.md) — **View location**
- [History](history.md) — **View route**
- [Reports](reports.md) — Alert report tab
- [Role-based authentication](role-based-authentication.md)

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| List | `GET /api/v1/alerts/` |
| Detail | `GET /api/v1/alerts/{id}/` |
| Auth | `Authorization: Bearer <access_token>` |
| Permission | `alerts` ≥ `view` |
| CSV export | None on this screen |
| Pagination | None |

## 2. Who can call it

| Role | Alerts | Vehicles shown |
|---|---|---|
| Super Admin | yes | All |
| Government Viewer | yes | Assigned constituencies |
| Constituency Head | yes | Assigned constituencies |
| Finance | **no** (`403`) | — |

Super Admin configures thresholds in Platform settings. Unassigned non-admin users get empty `alerts` and zero counts, not `403`.

## 3. Alert types

| `type` | Severity | When it fires | KPI card |
|---|---|---|---|
| `vehicle_started` | `info` | First start of the local day | yes |
| `vehicle_stopped` | `info` | A stop lasting at least `min_stop_minutes` (default 5) | no — filter only |
| `long_halt` | `warning` | Stationary longer than `long_halt_minutes` (default 60) | yes |
| `led_off` | `warning` | LED off while the vehicle is on duty | yes |
| `km_exceeded` | `critical` | Today's km over `daily_km_limit` (default 60) | yes |
| `gps_disconnected` | `critical` | GPS off, or no update for `stale_gps_minutes` (default 15) | yes |

`label` is a display string. For km exceeded it includes the configured cap, e.g. `"60 km daily limit exceeded"`.

Unread in the product sense = `warning` or `critical` that the browser has not opened. The API returns `unread_count` and `recent` (up to 6) for the current filters; keep opened IDs in `localStorage` and subtract them in the client.

## 4. List

**Title:** List alerts

**Endpoint:** `/api/v1/alerts/`

**Type:** `GET`

**Auth:** Bearer token, `alerts` ≥ `view`

**Query parameters:**

| Name | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| `date` | string | no | `today` | `today`, `yesterday`, or `YYYY-MM-DD` |
| `type` | string | no | `all` | `all` or one of the 6 types |
| `vehicle` | UUID | no | | Deep-link `?vehicle=` |
| `limit` | integer | no | | Truncate `alerts` (bell can use `limit=6`) |

`counts` ignore `type` so KPI cards stay stable while the table filters. `vehicle` scopes both counts and rows.

**Success response:** `200 OK`

```json
{
  "date": "2026-11-06",
  "focused_vehicle_id": null,
  "counts": {
    "total": 4,
    "km_exceeded": 1,
    "long_halt": 1,
    "led_off": 0,
    "gps_disconnected": 1,
    "vehicle_started": 3
  },
  "unread_count": 2,
  "recent": [],
  "alerts": [
    {
      "id": "2c1d0e11-aaaa-4bbb-8ccc-dd11ee22ff33",
      "type": "long_halt",
      "label": "Long halt detected",
      "severity": "warning",
      "vehicle_id": "7a1c2b90-1111-4aaa-8222-bb33cc44dd55",
      "vehicle_code": "GA-NG-AC01-V02",
      "registration": "GA08AA1002",
      "constituency_id": "4c29384c-b039-44c3-8207-ac293eda48db",
      "constituency": "Mandrem",
      "driver": { "id": "...", "name": "Suresh Kamat", "phone": "9822000000" },
      "created_at": "2026-11-06T08:15:00+00:00",
      "resolved_at": null,
      "description": "Long halt detected. Stationary for 90 min.",
      "lat": 15.66,
      "lng": 73.72,
      "address": "Mandrem depot",
      "today_km": 12.0,
      "speed_kmh": 0.0,
      "live_status": "long_halt",
      "attention": true,
      "exceeded": false
    }
  ]
}
```

Screen mapping:

| UI | Field |
|---|---|
| Date filter | `date=` |
| Category filter | `type=` |
| Vehicle filter | `vehicle=` |
| Total alerts | `counts.total` |
| 60 km daily limit exceeded | `counts.km_exceeded` |
| Long halt detected | `counts.long_halt` |
| LED TV switched off | `counts.led_off` |
| GPS disconnected | `counts.gps_disconnected` |
| Vehicle started | `counts.vehicle_started` |
| Table | `alerts` |
| Vehicle ID link | `/alerts/{id}` |
| Current live status | `live_status` |
| Orange left border | `severity` is `warning` or `critical` |
| Empty copy | `No alerts for this selection` when `alerts` is `[]` |
| Nav badge / bell count | `unread_count` minus locally read IDs |
| Bell dropdown | `recent` (max 6), empty copy `No unread alerts` |
| View all alerts | `/alerts` |

There is **no** mark-as-read on the list. Do not send a PATCH for that.

Constituency-scoped shortcut still exists: `GET /api/v1/constituencies/{id}/alerts/` (same permission).

## 5. Detail

**Title:** Alert detail

**Endpoint:** `/api/v1/alerts/{id}/`

**Type:** `GET`

**Auth:** Bearer token, `alerts` ≥ `view`

Unknown or out-of-scope IDs return `404` `{ "detail": "Alert not found." }`. Show **Alert not found**.

Opening this page is the client signal to mark the alert read in the browser.

```json
{
  "id": "2c1d0e11-aaaa-4bbb-8ccc-dd11ee22ff33",
  "type": "long_halt",
  "label": "Long halt detected",
  "severity": "warning",
  "description": "Long halt detected. Stationary for 90 min.",
  "created_at": "2026-11-06T08:15:00+00:00",
  "vehicle_id": "...",
  "vehicle_code": "GA-NG-AC01-V02",
  "registration": "GA08AA1002",
  "constituency": "Mandrem",
  "driver": { "name": "Suresh Kamat", "phone": "9822000000" },
  "today_km": 12.0,
  "daily_km_limit": 60,
  "current_speed_kmh": 0,
  "operating_min": 40,
  "current_status": "long_halt",
  "lat": 15.66,
  "lng": 73.72,
  "links": {
    "live_map": "/live-map?vehicle=...",
    "history": "/history/{vehicleId}/2026-11-06"
  },
  "timeline": [
    { "kind": "vehicle_started", "label": "Vehicle started", "at": "...", "address": "..." },
    { "kind": "long_halt", "label": "Long halt", "at": "...", "address": "...", "duration": "1h 30m" },
    { "kind": "last_point", "label": "Last recorded point", "at": "...", "address": "..." }
  ]
}
```

| UI | Field |
|---|---|
| Title | `label` |
| Description, severity, time | `description`, `severity`, `created_at` |
| Today's km vs daily limit | `today_km` / `daily_km_limit` |
| View location | `links.live_map` |
| View route | `links.history` |
| Map | `lat` / `lng` (Map / Satellite is client-only) |
| Timeline | `timeline` (`vehicle_started`, `stop` / `long_halt`, `last_point`) |

## 6. Errors

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown date." }` | Bad `date` |
| `400` | `{ "detail": "Unknown alert type." }` | Bad `type` |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Role cannot view alerts (Finance) |
| `404` | `{ "detail": "Alert not found." }` | Unknown id |
| `429` | `{ "detail": "..." }` | Rate limit |

## 7. Not on this API

- No CSV or PDF export from Alerts
- No mark-as-read endpoint (detail open + `localStorage` only)
- `vehicle_stopped` is filterable but has no KPI card
