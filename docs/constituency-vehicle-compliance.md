# Constituency, vehicle, and compliance APIs

Gaadi fleet APIs cover constituency-wise deployment, the vehicle directory, and compliance documents. Super Admin manages users and assigns constituencies. Every other user only sees the constituencies Super Admin assigned to them.

Base URL: `/api/v1/`

Send authenticated requests as:

```http
Authorization: Bearer <access_token>
```

## 1. Who can see what

Super Admin sees every constituency and vehicle.

Finance, Government Viewer, and Constituency Head only see constituencies in their assignment list. Role still decides *what they can do* (view drivers, approve documents, export). Role does not expand *which* constituencies they see.

If Super Admin assigns nothing, those users get empty lists and `404` on unassigned detail URLs.

Assign one or many constituencies:

`PUT /api/v1/users/{user_uuid}/assignments/`

```json
{
  "assignments": [
    { "scope_type": "constituency", "object_id": "<mandrem-uuid>" },
    { "scope_type": "constituency", "object_id": "<panaji-uuid>" }
  ]
}
```

Only Super Admin can create, replace, or delete assignments. `object_id` must be a real constituency UUID. Unknown IDs and duplicates return `400`. An empty `assignments` array clears the set.

You can also send the same list on `POST /api/v1/users/`, add one row with `POST /api/v1/users/{user_uuid}/assignments/`, or remove one with `DELETE /api/v1/users/{user_uuid}/assignments/{assignment_uuid}/`.

Assignment responses include resolved constituency `id`, `code`, `number`, `name`, and `district`.

## 2. Derived statuses

Constituency status is not stored:

| Status | Meaning |
|---|---|
| `operational` | At least one vehicle is not inactive, and none need attention or have exceeded the daily km limit |
| `needs_attention` | Any assigned vehicle needs attention or exceeded today's km limit |
| `inactive` | No vehicles, or every vehicle is inactive |

Vehicle operational status comes from the latest telemetry snapshot:

| Status | Meaning |
|---|---|
| `active` | Trip started and not in a long halt |
| `long_halt` | Speed ≤ 2 km/h for ≥ 60 minutes |
| `inactive` | Trip has not started today |

Directory filters: `active`, `attention`, `inactive`, `exceeded`. Attention is long halt, stale GPS (disconnected or no update for 15 minutes), or LED off while active. Exceeded is today's km greater than 60.

Document validity:

| Status | Meaning |
|---|---|
| `valid` | No end date, or more than 60 days left |
| `expiring_30` | Ends within 30 days |
| `expiring_60` | Ends in 31–60 days |
| `expired` | End date is in the past |

## 3. Constituencies

Module: `constituencies`. List and detail need `view`. Create and edit need `edit`.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/constituencies/` | `q`, `status`, `ordering=code\|name` |
| `POST` | `/constituencies/` | `name`, `district` (`north_goa` or `south_goa`), optional `number`, `lat`, `lng`, `image` |
| `GET` | `/constituencies/{uuid}/` | Rollup, vehicles, and today's derived alerts |
| `PATCH` | `/constituencies/{uuid}/` | Edit fields or image |
| `GET` | `/constituencies/{uuid}/vehicles/` | Vehicles in that constituency |
| `GET` | `/constituencies/{uuid}/map/` | Current lat/lng and status for live-map handoff |
| `GET` | `/constituencies/{uuid}/alerts/` | Needs `alerts` view |
| `GET` | `/constituencies/{uuid}/report/` | Needs `reports` view |

List rows include `code`, `number`, `name`, `image`, `total`, `active`, `inactive`, `attention`, and derived `status`.

Seed 40 Goa constituencies and a small demo fleet:

```bash
python manage.py seed_fleet
```

## 4. Vehicles

Module: `vehicles`. List and detail need `view`. Create and edit need `edit`.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/vehicles/` | `q` (code, registration, driver), `constituency`, `status` |
| `POST` | `/vehicles/` | Constituency, registration, driver, optional photos |
| `GET` | `/vehicles/{uuid}/` | Photos, driver, map point, today km vs 60, LED/GPS, documents, quick actions |
| `PATCH` | `/vehicles/{uuid}/` | Assignment, photos, driver, telemetry snapshot |
| `GET` | `/vehicles/{uuid}/alerts/` | Needs `alerts` view |

Vehicle codes look like `GA-NG-AC01-V01`. Finance users do not receive driver phone or licence numbers. They also only see `insurance` and `advertisement_license` documents.

Quick actions on vehicle detail:

- `live_map`: `/live-map?vehicle={id}`
- `history`: `/history?vehicle={id}`
- `share`: `null` (client copies the page URL)
- `notifications`: `/alerts?vehicle={id}`

## 5. Documents and expiry report

Viewing uses `compliance_documents`. Upload or replace needs `edit` on that module. Approve or reject needs `document_approvals` at `manage`. CSV export needs `export_data`.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/vehicles/{uuid}/documents/` | All eight types, including empty rows |
| `PUT` | `/vehicles/{uuid}/documents/{type}/` | Upload or replace file and dates; sets `approval=pending` |
| `POST` | `/vehicles/{uuid}/documents/{type}/review/` | `{ "decision": "approved"\|"rejected", "comment": "..." }` |
| `GET` | `/compliance/documents/` | `q`, `type`, `validity`, `approval`, `constituency` |
| `GET` | `/compliance/summary/` | pending, rejected, expired, expiring30, expiring60, missingUpload |
| `GET` | `/reports/documents/` | Rows plus chart counts. `export=csv` downloads a CSV |

Document types: `rc`, `insurance`, `puc`, `permit`, `fitness`, `election_commission`, `vehicle_photo_chassis`, `advertisement_license`.

## 6. Media

Uploaded images and document files are stored under `MEDIA_ROOT` (default `media/`) and served from `/media/` when `DEBUG=True`.

## 7. Tests

```bash
python manage.py test accounts fleet
```
