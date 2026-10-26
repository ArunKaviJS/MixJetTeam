# awery-backend — what it does, field by field

You (frontend) → **awery-backend** → **Awery ERP**. This service is the only piece
that talks to Awery. Nothing here touches email or the LLM — it starts from the
JSON the AI part already produced.

---

## 1. The big picture

```
 ┌─────────┐   email    ┌──────────────┐  extractedValues   ┌───────────────┐
 │  Gmail  │ ─────────▶ │   ai/  (LLM) │ ─────────────────▶ │  MongoDB      │
 └─────────┘            └──────────────┘  (writes a doc)     │ tb_file_details│
                                                             └──────┬────────┘
                                                                    │ read
                                              GET /files            │
 ┌──────────────┐   HTTP/JSON    ┌────────────────────────────┐  ◀──┘
 │  frontend/   │ ─────────────▶ │       awery-backend        │
 │  (React)     │ ◀───────────── │  FastAPI, port 8200        │
 └──────────────┘   JSON         └─────────────┬──────────────┘
        ▲   click "Proceed →"                  │ POST https://mixjetdev.awery.com/rpc/json/
        │                                      │ { "method": "createFlight", "params": [ {...} ] }
        │   flight_id, status                  ▼
        └──────────────────────────  ┌────────────────────┐
                                     │     Awery ERP      │
                                     └────────────────────┘
```

The backend has three jobs:

1. **Serve the file list / detail** to the frontend by reading MongoDB
   (`app/routers/files.py` + `app/db.py`).
2. **On "Proceed"**, convert the extracted fields into an Awery `createFlight`
   payload and call the Awery API (`app/mappers.py` + `app/awery_client.py`).
3. **Write the outcome back** onto the same Mongo document under an `awery` key.

---

## 2. How it connects to the Awery API

`app/awery_client.py`. Awery API v2 is **"HTTP over jRPC"**: one URL, every call is
a `POST` with a `method` name and a one-element `params` array.

| | |
|---|---|
| URL | `AWERY_ERP_API_URL` = `https://mixjetdev.awery.com/rpc/json/` (from `.env`) |
| Method | `POST` |
| Headers | `Content-Type: application/json`, `Authorization: Bearer <AWERY_ERP_API_BEARER_TOKEN>` |
| Body | `{ "method": "<name>", "params": [ { ...one object... } ] }` |

Response envelope (identical for every method):

```json
{ "jsonrpc": "2.0", "status": true, "message": "Ok", "data": { ... }, "suspend": false, "id": 1 }
```

- `status: true`  → `data` holds the result.
- `status: false` → the client raises `AweryError(message)` and the call is
  reported as failed (HTTP 400 from Awery is also treated as failure).

Only these methods are allowed (`config.ALLOWED_METHODS`) — `update*` / `delete*`
are deliberately not wired:

```
getFlight  getFlights  getFlightList  getCustomer  createFlight  insertFlights  createCustomer
```

Awery accepts **human names** instead of internal numeric ids via the `__name`
suffix (`customer__name`, `actype__name`, `actual_origin__name`), so the backend
does **not** need a separate "look up the id" round-trip.

---

## 3. Which fields are taken, and where they go

Source = the Mongo document's **`updatedExtractedValues` only**. `extractedValues`
is the AI's untouched original, kept as a log — this service never reads it for
mapping and never writes to it. Frontend edits (the "Update" button) also write to
`updatedExtractedValues` only. Mapping lives in `app/mappers.py :: build_create_flight()`.

### 3a. Flight header  (`params[0].flight`)

| From extraction | → Awery field | Notes |
|---|---|---|
| `Customer` | `customer__name` | e.g. `"Air Logistics Partners FZE"` |
| `Operator` (or `Customer` if empty) | `operator__name` | |
| `ACFT Type` | `actype__name` | e.g. `"A330-200F"` |
| `Reg No` (first token of `Reg No` + `Bulk Reg No`) | `aircraft__name` | e.g. `"TC-MAA"` |
| first `Flight` value in the schedule (or `flight_no` override) | `flight_no` | e.g. `"AZX7314"` |
| `Purposes` | `purpose__name` | |
| `Flight Type` | `flight_type` | lower-cased |
| Proceed option `company_name` | `company__name` | UI field, default "Awery Demo Company" |
| — constant — | `status: "planned"`, `payload_unit: "kg"`, `no_follow/positioning/autotrack: 0` | |
| Proceed option `unique` | `unique` | `[0]` = skip Awery duplicate check (UI checkbox), `[1]` = default algorithm |

### 3b. Waypoints  (`params[0].waypoints`)  — built from `Flight Schedule.items`

Each schedule row has `From` / `To` / `Departure` / `Arrival` / `Flight`.
The rows are flattened into an ordered list of airports (`VOMM → OMDB → LTFM → VOMM`):

| Per waypoint | Value |
|---|---|
| `prior` | 1, 2, 3, … (order) |
| `actual_origin__name` | ICAO pulled from `"Chennai International Airport (VOMM)"` → `VOMM` |
| `planned_departure_date` | this airport's `Departure`, normalised to `YYYY-MM-DD HH:MM:SS` |
| `planned_arrival_date` | this airport's `Arrival`, same normalisation |
| `call_sign` / `call_sign_landing` | the leg's `Flight` number |

Unparseable dates are passed through unchanged rather than dropped.

### 3c. `Flight Sectors` (the 11 permit rows)

Carried through untouched as `_permits_preview` in the built payload so the
frontend can show them, **but not sent to Awery** — none of the 7 allowed methods
creates a permit/service. Wiring permits is the next step to confirm with Awery.

### Worked example

Extraction (`6a844f7e987e02f0d0d4ad3c`, "Air Logistics Partners FZE") becomes:

```jsonc
{
  "method": "createFlight",
  "params": [{
    "flight": {
      "status": "planned", "payload_unit": "kg",
      "no_follow": 0, "positioning": 0, "autotrack": 0,
      "customer__name": "Air Logistics Partners FZE",
      "operator__name": "Air Logistics Partners FZE",
      "actype__name": "A330-200F",
      "aircraft__name": "TC-MAA",
      "flight_no": "AZX7314",
      "purpose__name": "Hazardous materials transport mission",
      "company__name": "Awery Demo Company"
    },
    "waypoints": [
      { "prior": 1, "actual_origin__name": "VOMM", "call_sign": "AZX7314",
        "planned_departure_date": "2024-05-03 01:00:00" },
      { "prior": 2, "actual_origin__name": "OMDB", "call_sign": "AZX7314",
        "call_sign_landing": "AZX7314",
        "planned_departure_date": "2024-05-04 03:00:00",
        "planned_arrival_date": "2024-05-03 04:30:00" },
      { "prior": 3, "actual_origin__name": "LTFM", "call_sign": "AZX7315",
        "call_sign_landing": "AZX7315",
        "planned_departure_date": "2024-05-05 02:15:00",
        "planned_arrival_date": "2024-05-04 08:15:00" },
      { "prior": 4, "actual_origin__name": "VOMM", "call_sign": "AZX7315",
        "call_sign_landing": "AZX7315",
        "planned_arrival_date": "2024-05-05 12:00:00" }
    ],
    "unique": [0]
  }]
}
```

Awery replies:

```json
{ "jsonrpc": "2.0", "status": true, "message": "Ok",
  "data": { "status": "ok", "message": "flight created", "flight_id": 38210 } }
```

---

## 4. What gets stored at the end

Nothing new is created in our DB — the **existing** `tb_file_details` document is
updated with one extra field:

```jsonc
// tb_file_details/<_id>
{
  ...,
  "updatedExtractedValues": { ... },      // unchanged unless the user hit "Update"
  "awery": {
    "status": "created",                  // "created" | "failed" | "pending"
    "flight_id": 38210,                   // Awery's flight id  ← the important result
    "flight_no": "AZX7314",
    "sent_payload": { "flight": {...}, "waypoints": [...], "unique": [0] },
    "response": { "jsonrpc": "2.0", "status": true, "data": { "flight_id": 38210, ... } },
    "error": null,
    "processed_at": "2026-09-09T18:41:12.004+00:00"
  }
}
```

On failure: `status: "failed"`, `error` holds Awery's message, `flight_id` absent,
and the endpoint returns HTTP 502 with the same `awery` object so the UI can show
what went wrong. The list view reads `awery.status` to render the **"Awery: created /
failed / not sent"** badge.

---

## 5. Endpoint reference

| Verb | Path | Purpose |
|---|---|---|
| GET | `/health` | config / token check |
| GET | `/files?page=&page_size=&search=` | list (scoped to `AVIATION_CLUSTER_ID`) |
| GET | `/files/{id}` | full Mongo document (form + PDF url + `awery`) |
| PUT | `/files/{id}` | save edited `updatedExtractedValues` ("Update" button) |
| DELETE | `/files/{id}` | remove the Mongo doc only (never calls Awery) |
| **POST** | **`/files/{id}/proceed`** | **the "Proceed →" button** — map + `createFlight` + store |
| GET | `/awery/flight` `/awery/flights` `/awery/flight-list` `/awery/customer` | direct Awery reads (Postman checks) |
| POST | `/awery/flight` `/awery/customer` `/awery/flights/insert` `/awery/rpc` `/awery/process` | direct Awery writes / passthrough |

`POST /files/{id}/proceed` body (all optional):

```jsonc
{ "dry_run": false,          // true = build payload, don't call Awery
  "create_customer": false,  // true = createCustomer before createFlight
  "company_name": "Awery Demo Company",
  "flight_no": null,         // override; else first Flight in the schedule
  "unique": [0] }            // Awery duplicate-check algorithm
```
