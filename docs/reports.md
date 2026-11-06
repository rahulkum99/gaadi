# Reports

Frontend integration guide for `/reports/:kind`.

Tabs shown depend on role. Data is scoped to the user's constituencies. Every tab except document-expiry has a date picker. Export is CSV only (no PDF). Hide Export when the role cannot export.

Related docs:

- [Platform settings](platform-settings.md) — expiry windows and daily km
- [Alerts](alerts.md)
- [History](history.md)
- [Live map](live-map.md)
- [Constituency, vehicle, and compliance](constituency-vehicle-compliance.md)

## 1. Quick facts

| Item | Value |
|---|---|
| Base URL | `/api/v1/` |
| Tab list | `GET /api/v1/reports/` |
| Report | `GET /api/v1/reports/{kind}/` |
| Auth | `Authorization: Bearer <access_token>` |
| Permission | `reports` ≥ `view`; CSV needs `export_data` ≥ `view` |
| Date | `date=today\|yesterday\|YYYY-MM-DD` (all kinds except `documents`) |

`{kind}` values: `daily`, `constituency`, `vehicle`, `route`, `alert`, `documents`. `document-expiry` is accepted as an alias of `documents`.

## 2. Access by role

| Role | Report tabs | Export |
|---|---|---|
| Super Admin | All 6 | Yes |
| Government Viewer | All 6 | Yes |
| Constituency Head | All 6, assigned data only | Yes |
| Finance | Daily, Constituency, Vehicle, Documents (no Route or Alert) | Yes for those tabs |

`GET /api/v1/reports/` returns the tabs the current user may open:

```json
{
  "kinds": ["daily", "constituency", "vehicle", "route", "alert", "documents"],
  "can_export": true,
  "default_kind": "daily"
}
```

If the UI lands on an invalid or forbidden tab, redirect to `default_kind` (the first allowed report). Calling a forbidden kind returns `403` with `{ "detail": "...", "allowed": [...] }`.

## 3. Daily report

`GET /api/v1/reports/daily/?date=today`

```json
{
  "kind": "daily",
  "date": "2026-11-06",
  "kpis": {
    "total_km": 102.5,
    "active": 3,
    "inactive": 1,
    "operating_min": 240,
    "operating": "4h",
    "halts": 6,
    "alerts": 4
  },
  "trend": [{ "date": "2026-10-31", "km": 80.0 }],
  "average_km": 90.2,
  "top_constituencies": [{ "id": "...", "code": "AC01", "name": "Mandrem", "vehicles": 2, "km": 30.0 }],
  "constituencies": []
}
```

CSV (`?export=csv`) is the constituency table: `code`, `name`, `vehicles`, `km`.

| UI | Field |
|---|---|
| Total kilometres | `kpis.total_km` |
| Active / inactive vehicles | `kpis.active` / `kpis.inactive` |
| Operating duration | `kpis.operating` |
| Total halts | `kpis.halts` |
| Total alerts | `kpis.alerts` |
| 7-day km trend | `trend` with average line `average_km` |
| Top 10 constituencies | `top_constituencies` |
| Constituency table | `constituencies` |

## 4. Constituency report

`GET /api/v1/reports/constituency/?date=today&constituency=<uuid>`

`constituency` is optional focus (`?constituency=`).

Columns: `code` + `name`, `assigned`, `active`, `inactive`, `total_km`, `avg_km`, `alerts`.

CSV: the same columns.

## 5. Vehicle report

`GET /api/v1/reports/vehicle/?date=today`

Columns: Vehicle ID + registration (`code`, `registration`), `constituency`, `driver`, `km`, `operating`, `stops`, `halts` (long halts), `alerts`, `status`.

CSV: `code`, `registration`, `constituency`, `driver`, `km`, `operating`, `stops`, `halts`, `alerts`, `status`.

## 6. Route report

`GET /api/v1/reports/route/?date=today`

Only vehicles that started that day (have distance). Finance cannot open this tab.

Columns: `code` / `registration`, `start`, `end`, `km`, `operating`, `halt`, `stops`.

## 7. Alert report

`GET /api/v1/reports/alert/?date=today`

Finance cannot open this tab.

`kpis` is a count per alert type present that day (plus `total`). Table rows: `time`, `type`, `vehicle`, `constituency`, `description`.

CSV columns: `time`, `type`, `vehicle`, `constituency`, `description`.

## 8. Document-expiry report

`GET /api/v1/reports/documents/` (also `/reports/document-expiry/`)

No date picker. Validity windows use platform settings (`expire_soon_days` / `expire_watch_days` / `approach_ratio`).

**Query:** `q`, `type`, `validity`, `constituency` (same filters as compliance documents).

| `type` | Label |
|---|---|
| `rc` | Registration Certificate (RC) |
| `insurance` | Vehicle insurance |
| `puc` | Pollution Under Control (PUC) |
| `permit` | Vehicle permit |
| `fitness` | Fitness certificate |
| `election_commission` | Election Commission approval |
| `vehicle_photo_chassis` | Vehicle photo & chassis |
| `advertisement_license` | Advertisement license |

`validity`: `all`, `valid`, `expiring_30` (30 days), `expiring_60` (31–60 days), `expired`.

```json
{
  "kind": "documents",
  "counts": { "total": 12, "valid": 8, "expiring_30": 2, "expiring_60": 1, "expired": 1 },
  "rows": [
    {
      "vehicle_id": "...",
      "vehicle_code": "GA-NG-AC01-V01",
      "registration": "GA08AA1001",
      "constituency": "Mandrem",
      "type": "insurance",
      "label": "Vehicle insurance",
      "end_date": "2026-11-16",
      "validity": "expiring_30"
    }
  ]
}
```

| UI | Field |
|---|---|
| Donut + center total | `counts` (`valid`, `expiring_30`, `expiring_60`, `expired`, `total`) |
| Search | `q=` vehicle ID or registration |
| Document type filter | `type=` |
| Validity filter | `validity=` |
| Constituency filter | `constituency=` |
| Table | Vehicle ID + registration, constituency, document type (`label`), validity, `end_date` |
| Export CSV | `?export=csv` of the filtered rows |

Finance only sees insurance and advertisement-license documents (same rule as the compliance module).

## 9. Errors

| Status | Body | When |
|---|---|---|
| `400` | `{ "detail": "Unknown report.", "allowed": [...] }` | Bad `kind` |
| `400` | `{ "detail": "Unknown date." }` | Bad `date` |
| `403` | `{ "detail": "This report is not available for your role.", "allowed": [...] }` | Finance on route/alert |
| `401` / `429` | `{ "detail": "..." }` | Auth / rate limit |

## 10. Not on this API

- PDF export (CSV only)
- Route and Alert tabs for Finance
