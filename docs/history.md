# History

Frontend integration guide for `/history` and `/history/:vehicleId/:date`.

History is built from GPS points saved every 5 minutes. Docker Compose runs this in the `live-ingest` service (`python manage.py pull_live_fleet` on a 300s loop). Live Map GET also writes a snapshot if that interval has passed. Stop detection uses platform settings: stops shorter than `min_stop_minutes` are ignored; stops at or above `long_halt_minutes` are long halts. Operating minutes accumulate only inside `operating_start_hour`–`operating_end_hour`.

There is no route playback. An old `/playback` URL should open History.

Related docs:

- [Platform settings](platform-settings.md)
- [Live map](live-map.md)
- [Alerts](alerts.md)
- [Reports](reports.md)

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| List | `GET /api/v1/history/` |
| Day / route | `GET /api/v1/history/{vehicleId}/{YYYY-MM-DD}/` |
| Auth | `Authorization: Bearer <access_token>` |
| Permission | `vehicle_history` ≥ `view` |
| CSV export | None on this screen |

## 2. Who can call it

| Role | History | Vehicles shown |
|---|---|---|
| Super Admin | yes | All |
| Government Viewer | yes | Assigned constituencies |
| Constituency Head | yes | Assigned constituencies |
| Finance | **no** (`403`) | — |

## 3. History list

**Endpoint:** `/api/v1/history/`

**Type:** `GET`

**Query parameters:**

| Name | Type | Required | Default | Allowed values |
|---|---|---|---|---|
| `vehicle` | UUID | no | First scoped vehicle | Deep-link `?vehicle=` |
| `range` | string | no | `today` | `today`, `yesterday`, `last_7`, `custom` |
| `from` | `YYYY-MM-DD` | for `custom` | | Inclusive start |
| `to` | `YYYY-MM-DD` | for `custom` | | Inclusive end, max 31 days |

If `vehicle` is omitted, the API selects `vehicles[0]` and returns it as `vehicle`. If the user has no vehicles, `vehicle` is `null` and KPIs are zero.

**Success response:** `200 OK`

```json
{
  "vehicles": [
    { "id": "...", "code": "GA-NG-AC01-V01", "registration": "GA08AA1001", "label": "GA-NG-AC01-V01 · GA08AA1001" }
  ],
  "vehicle": { "id": "...", "code": "GA-NG-AC01-V01", "registration": "GA08AA1001" },
  "range": { "from": "2026-11-06", "to": "2026-11-06" },
  "kpis": {
    "total_km": 18.5,
    "avg_km": 18.5,
    "operating_min": 95,
    "operating": "1h 35m",
    "halt_min": 20,
    "halt": "20m",
    "stops": 2,
    "long_halts": 0
  },
  "average_km": 18.5,
  "chart": [{ "date": "2026-11-06", "km": 18.5 }],
  "days": [
    {
      "date": "2026-11-06",
      "start": "2026-11-06T02:30:00+00:00",
      "end": "2026-11-06T11:00:00+00:00",
      "km": 18.5,
      "operating": "1h 35m",
      "operating_min": 95,
      "halt": "20m",
      "halt_min": 20,
      "stops": 2,
      "long_halts": 0,
      "status": "active"
    }
  ]
}
```

| UI | Field |
|---|---|
| Vehicle selector | `vehicles` (`label` is `ID · registration`) |
| Date range | `range=today\|yesterday\|last_7` or `range=custom&from=&to=` |
| Total distance | `kpis.total_km` |
| Average km / day | `kpis.avg_km` (also `average_km` for the chart reference line) |
| Operating duration | `kpis.operating` |
| Halt time | `kpis.halt` |
| Stops | `kpis.stops` |
| Long halts (orange) | `kpis.long_halts` |
| Daily mileage bars | `chart[].km` vs `date`; orange average = `average_km` |
| Day table | `days` |
| Date link | `/history/{vehicleId}/{date}` |
| Status badge | `inactive` / `active` / `long_halt` |

Unknown vehicle: `404`. Bad range: `400`.

## 4. History day / route

**Endpoint:** `/api/v1/history/{vehicleId}/{YYYY-MM-DD}/`

**Type:** `GET`

```json
{
  "vehicle": { "id": "...", "code": "GA-NG-AC01-V01", "registration": "GA08AA1001" },
  "date": "2026-11-06",
  "empty": false,
  "kpis": {
    "km": 18.5,
    "operating": "1h 35m",
    "operating_min": 95,
    "halt": "20m",
    "halt_min": 20,
    "stops": 2,
    "long_halts": 0
  },
  "start": { "lat": 15.66, "lng": 73.72, "captured_at": "..." },
  "end": { "lat": 15.67, "lng": 73.73, "captured_at": "..." },
  "polyline": [{ "lat": 15.66, "lng": 73.72, "captured_at": "..." }],
  "stops": [
    {
      "number": 1,
      "location": "Mandrem beach road",
      "lat": 15.661,
      "lng": 73.719,
      "arrival": "...",
      "departure": "...",
      "duration_min": 12,
      "duration": "12m",
      "km_so_far": 4.2,
      "long_halt": false
    }
  ],
  "points": []
}
```

| UI | Field |
|---|---|
| Header | `vehicle.code` · `vehicle.registration` |
| Title | Route on `date` |
| Back | `/history?vehicle={id}` |
| Empty copy | `No history for this day` when `empty` is `true` |
| KPIs | `kpis.km`, `operating`, `halt`, `stops`, `long_halts` |
| Route line | `polyline` |
| Start marker (green) | `start` |
| End marker (navy) | `end` |
| Numbered stops | `stops`; amber when `long_halt` is `true` |
| Stop tooltip | `number` · `duration` |
| Map / Satellite | Client-only |
| Stop table | number, `location`, `arrival`, `departure` (null → —), `duration`, `km_so_far` |
| Empty stop row | `No stops recorded` when `stops` is `[]` |

## 5. Errors

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown date." }` | Bad day in the URL |
| `400` | `{ "detail": "Custom range needs from and to dates." }` | `range=custom` without dates |
| `401` | `{ "detail": "..." }` | Missing or expired token |
| `403` | `{ "detail": "..." }` | Finance, or role without history |
| `404` | `{ "detail": "Not found." }` | Unknown or out-of-scope vehicle |
| `429` | `{ "detail": "..." }` | Rate limit |

## 6. Not on this API

- No CSV export
- No playback / replay
- Snapshots older than the 5-minute cadence are not invented; a day with no points is empty (today can fall back to the latest telemetry)
