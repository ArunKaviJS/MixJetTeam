# Email → Awery ERP — field mapping

*Checked live against `https://mixjetdev.awery.com/rpc/json/` with the API token on
2026-09-10. Read-only calls only — nothing was created or changed.*

## 1. What this project is

Permit-request email → AI extracts fields → this backend calls the Awery ERP API
and fills an **existing** flow: one **Flight** (+ its sectors) and one **Service**
row per permit. We only map what the email gives — no invented data.

```
Email ─▶ AI extract ─▶ backend ─▶ getCustomer / getFlightList   (check, read-only)
                              ─▶ createFlight + insertFlights    (flight + sectors)
                              ─▶ service per permit              ⛔ NO API METHOD (see §4)
```

Sample email = mission MAA–DXB–LTFM, A330-200F TC-MAA, 3 legs, 11 permits.

---

## 2. X = what the email gives us

| # | Item | Value (this sample) |
|---|---|---|
| X1 | Charterer / customer | Air Logistics Partners FZE — ops@airlogpartners.ae, +971 55 873 5100, DAFZA |
| X2 | Aircraft type | A330-200F |
| X3 | Registration | TC-MAA (alt TC-MAB, TC-MAC) |
| X4 | Purpose | Hazardous materials transport mission |
| X5 | 3 sectors | 03MAY24 AZX7314 VOMM 0100→OMDB 0430 · 04MAY24 AZX7315 OMDB 0300→LTFM 0815 · 05MAY24 AZX7315 LTFM 0215→VOMM 1200 |
| X6 | Load / sector | EMPTY FERRY/TECHSTOP · LOADED/MAINTENANCE SUPPLIES · LOADED/BACKHAUL COMPONENTS |
| X7 | Payload | OMDB–LTFM ≈ 34 tons (leg 2 only) |
| X8 | Cargo | Aviation maintenance chemicals, paint hardeners, battery packs |
| X9 | Dangerous goods | UN1263 Paint materials, Class 3 |
| X10 | 11 permits | see §5 |
| X11 | Consignor | MAA Aerospace Maintenance Pvt Ltd, Chennai — ops@maaam.in |
| X12 | Consignee | Turkish Aerospace Maintenance Center, Istanbul — ops-tr@tamc.aero |

---

## 3. Y = mapping to Awery **Flight**  (`createFlight` → `params[0].flight`)

| Awery field (API key) | Source | Value now | State |
|---|---|---|---|
| `customer__name` | X1 | Air Logistics Partners FZE | ❗ **not found in test DB** (tried 4 spellings) → client must add it, or we `createCustomer` |
| `operator__name` | — | — | ❌ **missing** — not in email |
| `actype__name` | X2 | A330-200F | ⚠ confirm exact Awery code |
| `aircraft__name` | X3 | TC-MAA | ✅ |
| `flight_no` (per sector) | X5 | AZX7314 / AZX7315 / AZX7315 | ✅ |
| `purpose__name` | X4 | Hazardous materials transport mission | ⚠ must match an Awery Purpose value |
| `flight_type` | X4/X6 | `cargo` | ⚠ API enum — seen live: `international`, `domestic`, `coload` |
| `status` | — | `planned` | ✅ live values: `planned`, `completed` |
| `company__name` | fixed | **MixJet UAE** (code `MIX`) | ✅ confirmed from live customer record |
| `payload_unit` | fixed | `kg` | ✅ |

### Per **Sector** (`waypoints[]` — one flight record, sector flight-no differs)

| Awery key | Source | Leg 1 / 2 / 3 | State |
|---|---|---|---|
| `actual_origin__name` | X5 | VOMM / OMDB / LTFM (ICAO) | ✅ |
| `prior` | order | 1 / 2 / 3 (+ final arrival wp) | ✅ |
| `call_sign` / `call_sign_landing` | X5 | AZX7314 / AZX7315 | ✅ |
| `planned_departure_date` | X5 | 2024-05-03 01:00 / 05-04 03:00 / 05-05 02:15 | ⚠ confirm year 2024 & UTC |
| `planned_arrival_date` | X5 | 2024-05-03 04:30 / 05-04 08:15 / 05-05 12:00 | ⚠ same |
| `available_payload` | X7 | — / 34000 / — | ⚠ leg 2 only |
| `empty_leg` | X6 | true / false / false | ✅ derivable from "EMPTY FERRY" |
| load text, offload, pax, crew | X6 / — | text only; rest missing | ⚠/❌ |

Flight time & local times: **Awery computes them** — leave blank.

---

## 4. Y = mapping to Awery **Service** (per permit)  ⛔ BLOCKED

**The API token has no method to read or create flight Services.**
Verified live — every guess (`getServices`, `getFlightServices`, `getServiceList`,
`getServicesByFlight`, `getPermits`, …) returns **"Method … Not Allowed"**, and
`getFlight` returns only `flight` + `waypoints` + `awbs` (no services).
`createFlight` / `updateFlight` / `insertFlights` accept **only** `flight` +
`waypoints` — no service/permit key exists in the whole API.

So §5 below is the intended mapping, but it **cannot be sent** until the client
either enables a service method on the API or accepts manual entry.

Intended fill (Type → Supplier, per your note):

| Awery service field | Source | Value | State |
|---|---|---|---|
| Type | X10 | mapped permit type | ⚠ need Awery service-type list |
| Service No | — | — | ❌ auto by Awery? or blank |
| Ref. No | — | email subject / request id? | ❌ decide rule |
| Status | screenshot | `Original` / `Requested` | ⚠ confirm |
| Schedule status | — | — | ❌ |
| Arrival | X5 | sector arrival UTC for that country | ⚠ partial |
| Sequence | derived | 1…11 | ✅ |
| Urgency | screenshot | `URGENT` | ⚠ constant? |
| Through | screenshot | `Empty` | ⚠ constant? |
| Payment / Quantity | — | — / 1 | ❌ / assume |
| Validity From–To | X5 | sector date(s) | ⚠ partial |
| Client Type / Client | fixed / X1 | `Customer` / Air Logistics Partners FZE | ✅ |
| Supplier | — | handling agent per country | ❌ do you keep defaults per country? |

---

## 5. The 11 permit rows

| Seq | Sector | Flight | Country | Email token | → Service Type |
|---|---|---|---|---|---|
| 1 | VOMM–OMDB | AZX7314 | India | DG Clearance | Dangerous Goods |
| 2 | VOMM–OMDB | AZX7314 | Oman | OVF | Overflight |
| 3 | VOMM–OMDB | AZX7314 | UAE | TECH | Technical Stop |
| 4 | OMDB–LTFM | AZX7315 | Saudi Arabia | OVF | Overflight |
| 5 | OMDB–LTFM | AZX7315 | Jordan | OVF | Overflight |
| 6 | OMDB–LTFM | AZX7315 | Türkiye | TFC | Traffic Rights |
| 7 | OMDB–LTFM | AZX7315 | Türkiye | DG Approval | Dangerous Goods |
| 8 | LTFM–VOMM | AZX7315 | Türkiye | OVF | Overflight |
| 9 | LTFM–VOMM | AZX7315 | Egypt | OVF | Overflight |
| 10 | LTFM–VOMM | AZX7315 | Oman | OVF | Overflight |
| 11 | LTFM–VOMM | AZX7315 | India | TFC | Traffic Rights |

DG rows (1, 7) also carry UN1263 / Paint materials / Class 3 (X9).

---

## 6. Missing — must come from elsewhere

| Field | For | Source needed |
|---|---|---|
| **Operator** | Flight (required) | client default / rule (AOC holder?) |
| **Customer record** | Flight (required) | "Air Logistics Partners FZE" isn't in Awery — add it or allow `createCustomer` |
| Flight type / Purpose exact values | Flight | Awery picklist |
| ACFT type exact code | Flight | Awery aircraft list |
| **Service method** | all 11 permits | **Awery must expose one** — hard blocker |
| Service Type / Status / Schedule status | Services | Awery service config |
| Ref. No rule, Supplier per country | Services | business decision |
| Payload legs 1 & 3, MTOW, crew, pax | Sectors | usually optional — confirm |

---

## 7. Questions for the client

1. **Service/permit via API** — is there a method (or can Awery add one)? Right now
   the API cannot create the 11 service rows at all.
2. **Operator** for MixJet permit flights — fixed default or per mission?
3. "**Air Logistics Partners FZE**" is not in the test DB — will you add customers,
   or should we `createCustomer` automatically?
4. Send the picklists for **Flight type**, **Purpose**, **Service Type**,
   **Service Status**, **Schedule status** (or a screen of each).
5. **Ref. No** on a service — email subject / permit-request no / blank?
6. **Supplier** per permit — default handling agents per country, or leave blank?
7. Email sector times — always **UTC**? Year `24` → confirm 2024.
8. Duplicate rule — same callsign+date+route exists → skip / update / new?

---

## 8. API methods — verified behaviour

| Method | What it actually does (live) | Use |
|---|---|---|
| `getCustomer` | `{customer__name}` / `{id}` / `{customer_code}` → customer record (id, `company__name`, country) | resolve / verify customer |
| `getFlightList` | `{from_date,to_date,date_type}` → `data.data_list[]`. **Date range only** — no `flight_no` filter | duplicate scan |
| `getFlight` | `{flight_id}` (safe) or `{flight_no}` (errors if duplicate) → `flight` + `waypoints` + `awbs`. **No services** | verify after create |
| `getFlights` | params `[[{flight_id|flight_no}]]` → batch get-by-id (not a search) | fetch several by id |
| `createFlight` | `{flight, waypoints}` → `data.flight_id`. No service field | create header + legs |
| `insertFlights` | same shape; also updates if duplicate. `unique:[0..5]` picks the dup algorithm | add/replace legs |
| `updateFlight` | `{flight:{id,…}, waypoints:[]}` → change status/fields | post-create edits |
| `getServices*` / `getPermits` | **"Method Not Allowed"** — do not exist | — |

Postman check (read-only), `Authorization: Bearer <token>`:
```
{ "method":"getCustomer",  "params":[ {"customer__name":"Hunnu Air"} ] }
{ "method":"getFlight",     "params":[ {"flight_id":38132} ] }          // MIX25375
{ "method":"getFlightList", "params":[ {"from_date":"2026-09-04","to_date":"2026-09-05","date_type":"departure_date"} ] }
```

### Real response shapes (trimmed)

`getCustomer` → `data.customer`: `id, customer_name, customer_code, country__name,
company__name ("MixJet UAE"), company_code ("MIX"), main_email, main_phone, city`.

`getFlight` → `data.flight`: `flight_id, status, flight_type, call_sign,
planned_departure_date, planned_arrival_date, path_icao, path_iata, reg_no, actype,
operator__name, origin_icao, dest_icao` + `data.waypoints[]`: `icao, call_sign,
planned_departure_date, planned_arrival_date, available_payload, deplaned_pax,
crew_exists, offload_weight` + `data.awbs[]`.

---

## 9. Bottom line

- **Flight + 3 sectors** → doable now with `createFlight` + `insertFlights`. Blockers
  are just values: **Operator**, the **customer record**, and exact enum spellings.
- **11 permit/service rows** → **not doable with the current API.** Needs Awery to
  expose a service method (Q1) — otherwise permits stay manual.
