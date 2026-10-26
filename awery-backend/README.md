# awery-backend

Standalone service that takes the **AI extraction JSON** (produced by [`../ai`](../ai))
and pushes it into **Awery ERP** through the Awery API v2.

- Awery API v2 = *HTTP over jRPC*: one endpoint `POST {url}/rpc/json/`, body
  `{ "method": "...", "params": [ { ... } ] }`, auth via `Authorization: Bearer <token>`.
- Response envelope: `{ "jsonrpc", "status": true|false, "message", "data", "suspend", "id" }`.
- **No `update*` / `delete*` methods are exposed** (by request). Allowed:
  `getFlight, getFlights, getFlightList, getCustomer, createFlight, insertFlights, createCustomer`.

> **New:** this service also backs the React `../frontend`. It reads the AI
> pipeline's Mongo documents (`GET /files`, `GET /files/{id}`) and the **Proceed**
> button hits `POST /files/{id}/proceed`. Full walkthrough of the mapping and what
> gets stored: **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**.

## Endpoints for the frontend

| Verb | Path | Purpose |
|---|---|---|
| GET | `/files?page=&page_size=&search=` | list Aviation Permit Requests (scoped to `AVIATION_CLUSTER_ID`) |
| GET | `/files/{id}` | full Mongo doc — form values, PDF url, `awery` result |
| PUT | `/files/{id}` | save edited `updatedExtractedValues` |
| DELETE | `/files/{id}` | delete the Mongo doc only (never calls Awery) |
| POST | `/files/{id}/proceed` | map extraction → `createFlight` → store `awery` on the doc |

`proceed` body (all optional): `{ "dry_run", "create_customer", "company_name", "flight_no", "unique" }`.
Requires `MONGO_URI` in `.env`.

```
awery-backend/
  app/
    config.py        env + allowed-method whitelist
    awery_client.py  low-level jRPC caller (auth, envelope handling, errors)
    schemas.py       request models incl. the AI extraction shape
    mappers.py       AI extraction  ->  Awery createFlight / createCustomer payloads
    main.py          FastAPI app (CORS for the React frontend)
    routers/
      health.py      GET /health
      read.py        GET  /awery/customer|flight|flight-list|flights   (checks)
      write.py       POST /awery/customer|flight|flights/insert|rpc|process
  postman/
    MixJet-Awery-Backend.postman_collection.json   test THIS backend
    Awery-ERP-Direct.postman_collection.json       test Awery jRPC directly
  run.py             uvicorn on AWERY_BACKEND_PORT (default 8200)
```

## 1. Setup

```bash
cd awery-backend
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # cp on macOS/Linux
```

Edit `.env` and set the real token (leave everything else as-is):

```
AWERY_ERP_API_URL=https://mixjetdev.awery.com/rpc/json/
AWERY_ERP_API_BEARER_TOKEN=<<< paste the real perpetual token here >>>
```

If Awery expects the bare token (no `Bearer ` prefix), set `AWERY_AUTH_SCHEME=raw`.

## 2. Run

```bash
python run.py
```

- Swagger UI: <http://127.0.0.1:8200/docs>
- Health:     <http://127.0.0.1:8200/health>

## 3. Endpoints

### GET (checks — use these first in Postman)

| Endpoint | Awery method | Example |
|---|---|---|
| `GET /awery/flight?flight_no=MIX22985` | `getFlight` | existing flight |
| `GET /awery/flight?flight_id=535083` | `getFlight` | by id |
| `GET /awery/flights?flight_no=MIX22985` | `getFlights` | |
| `GET /awery/flight-list?from_date=2024-05-01&to_date=2024-07-31&date_type=departure_date` | `getFlightList` | |
| `GET /awery/customer?id=64710` | `getCustomer` | also `customer_code=` / `slx_id=` |

> `flight_no=MIX22985` exists in the current Awery instance — use it for a positive
> `getFlight` test. Any other number should come back `status:false / "flight not found"`.

### POST (writes)

| Endpoint | Awery method | Body |
|---|---|---|
| `POST /awery/process` | `createFlight` (+ optional `createCustomer`) | **main frontend trigger** — see below |
| `POST /awery/customer` | `createCustomer` | `{ "customer": {...}, "contacts": [...] }` |
| `POST /awery/flight` | `createFlight` | `{ "flight": {...}, "waypoints": [...] }` |
| `POST /awery/flights/insert` | `insertFlights` | `{ "flight": {...}, "waypoints": [...] }` |
| `POST /awery/rpc` | any allowed method | `{ "method": "...", "params": {...} }` |

### `POST /awery/process` — the frontend click

```jsonc
{
  "extracted":  { ...AI extraction JSON... },   // OR "mongo_id": "<tb_file_details _id>"
  "dry_run":    true,                            // true = build payload, don't send
  "create_customer": false,                      // true = createCustomer first
  "company_name": "Awery Demo Company",          // -> company__name
  "flight_no":  null,                            // override; else taken from the schedule
  "unique":     [0]                              // Awery dup-check: [0]=skip, [1]=default
}
```

`extracted` is exactly what the AI part stores in Mongo under `extractedValues`
(keys `Customer`, `Reg No`, `ACFT Type`, `Flight Schedule`, `Flight Sectors`, …).
`mappers.py` turns it into:

```jsonc
{ "flight": { "customer__name": "...", "operator__name": "...", "aircraft__name": "TC-MAA",
              "actype__name": "A330-200F", "flight_no": "AZX7314", "purpose__name": "...",
              "flight_type": "cargo", "company__name": "...", "status": "planned",
              "payload_unit": "kg" },
  "waypoints": [ { "prior": 1, "actual_origin__name": "VOMM",
                   "planned_departure_date": "2024-05-03 01:00:00", "call_sign": "AZX7314" }, ... ] }
```

Airport ICAO is pulled from `"... (VOMM)"`; dates are normalised to
`YYYY-MM-DD HH:MM:SS` (unparseable values pass through unchanged).

Permit rows (`Flight Sectors`) are returned under `_permits_preview` but **not**
sent yet — wiring permits/services into Awery is the next step to confirm with them.

## 4. How to check in Postman

### A. Test this backend (recommended path)

1. `python run.py`
2. Import `postman/MixJet-Awery-Backend.postman_collection.json`.
3. Collection variables: `base_url = http://127.0.0.1:8200`, `sample_flight_no = MIX22985`.
4. Run in order:
   - **health** → `token_configured: true`.
   - **getFlight (existing flight_no)** → Awery envelope with `status: true` and the `MIX22985` flight.
   - **getFlight** with any other number → `status: false`, message “flight not found” (proves the lookup works).
   - **getFlightList**, **getCustomer** → `status: true` with data.
   - **process (dry_run)** → returns `create_flight_payload` only. Inspect it.
   - **process (LIVE)** → actually calls `createFlight`; response has `flight_id`.
     Then re-run **getFlight** with that `flight_no` to confirm.

### B. Test Awery directly (no backend)

1. Import `postman/Awery-ERP-Direct.postman_collection.json`.
2. Set collection variables `url = https://mixjetdev.awery.com` and `token = <real token>`.
   (Auth is preset to Bearer `{{token}}` at collection level.)
3. Send **getFlight (existing flight_no)** — body is:
   ```json
   { "method": "getFlight", "params": [ { "flight_no": "MIX22985" } ] }
   ```
   Expect HTTP 200 + `"status": true`. Errors come back HTTP 400 + `"status": false`.
4. `getFlights`, `getFlightList`, `getCustomer` the same way. `createFlight` /
   `createCustomer` / `insertFlights` bodies are filled with working samples — send
   when you're ready to write. Keep `"unique": [0]` while testing to skip dup checks.

## 5. Next (frontend)

React app calls `POST {AWERY_BACKEND}/awery/process` with the reviewed extraction
(or `mongo_id`) when the user clicks **“Send to Awery”**. CORS origins are set via
`AWERY_CORS_ORIGINS` in `.env`.
