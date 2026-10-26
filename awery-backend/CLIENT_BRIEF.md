# Awery Integration — status & open points

*Verified live against `https://mixjetdev.awery.com/rpc/json/` (read-only) + the
published Postman collection, 2026-09-10.*

Legend: **X** = value the email gives us · **Y** = where it goes in Awery (field / method) · **Z** = missing → ask client

---

## 1. In one line

Permit email → AI extracts fields → backend calls Awery API to create **1 Flight +
its sectors**, then **1 Service row per permit**.

## 2. Status

| Part | Method | Status |
|---|---|---|
| Flight header | `createFlight` | ✅ works — needs a few values (Z) |
| Sectors / legs | `insertFlights` (or waypoints in `createFlight`) | ✅ works — needs a few values (Z) |
| Customer lookup | `getCustomer` | ✅ works (by `customer__name` / `id` / `code`) |
| Duplicate check | `getFlightList` (date range) | ✅ works |
| **Services / permits** | — | ⛔ **no API method or parameter exists** — see §6 |

---

## 3. FLIGHT header — X → Y → Z

| Awery field (`flight.*`) | X — from email | Y — value we'd send | Z — gap / ask |
|---|---|---|---|
| `customer__name` | Charterer = "Air Logistics Partners FZE" | same | ❗ not in Awery DB — client adds it, or allow `createCustomer`? |
| `operator__name` | — | — | ❌ **not in email** — fixed default for MixJet permit flights? |
| `company__name` | — | **MixJet UAE** (code MIX) | ✅ confirmed from live data — OK to hard-code? |
| `aircraft__name` | Reg "TC-MAA" (alt TC-MAB/MAC) | TC-MAA | ✅ |
| `actype__name` | "A330-200F" | A330-200F | ⚠ exact Awery code? (list needed) |
| `flight_no` (per leg) | AZX7314 / AZX7315 | same | ✅ |
| `purpose__name` | "Hazardous materials transport mission" | mapped value | ⚠ must match an Awery Purpose — send list |
| `flight_type` | derived (cargo) | `cargo` | ⚠ Awery enum — send list (live values seen: international/domestic/coload) |
| `status` | — | `planned` | ✅ (confirm default) |
| `payload_unit` | — | `kg` | ✅ |

## 4. SECTORS — X → Y → Z  (3 legs)

| Awery field (`waypoints[].*`) | X — from email | Y — value | Z — gap / ask |
|---|---|---|---|
| `actual_origin__name` | VOMM / OMDB / LTFM (from "… (VOMM)") | ICAO | ✅ |
| `prior` | leg order | 1,2,3 (+ final arrival wp) | ✅ |
| `call_sign` / `call_sign_landing` | AZX7314 / AZX7315 | same | ✅ |
| `planned_departure_date` | "03MAY24 0100" etc. | 2024-05-03 01:00:00 | ⚠ confirm **year = 2024** and times = **UTC** |
| `planned_arrival_date` | "0430" etc. | 2024-05-03 04:30:00 | ⚠ same |
| `available_payload` | "OMDB–LTFM ≈ 34 tons" | 34000 (leg 2 only) | ⚠ legs 1 & 3 not given |
| `empty_leg` | "EMPTY FERRY" (leg 1) | true / false / false | ✅ derivable |
| Load text | "EMPTY FERRY/TECHSTOP" … | store as note | ✅ |
| offload / pax / crew / MTOW | — | — | ❌ not in email — needed? (usually optional) |

Flight time & local times → **Awery computes**, leave blank.

## 5. SERVICES / PERMITS — X → Y → Z  (11 rows)

**Y is blank because there is no Awery API method/parameter for services (§6).**
This is the intended mapping once a method exists:

| Awery service field | X — from email | Y (intended) | Z — gap / ask |
|---|---|---|---|
| Type | permit token (DG / OVF / TECH / TFC) per row | mapped service type | ⚠ Awery service-type list |
| Country | India, Oman, UAE, … | same | ✅ |
| Sector / Flight No | VOMM-OMDB / AZX7314 … | same | ✅ |
| Sequence | row order | 1…11 | ✅ |
| Client Type / Client | — / charterer | Customer / Air Logistics Partners FZE | ✅ |
| Status | — | "Requested" / "Original" | ⚠ enum + default? |
| Schedule status | — | — | ❌ |
| Service No | — | — | ❌ auto by Awery or we set? |
| Ref. No | — | — | ❌ **rule?** (email subject / permit-req no / blank) |
| Arrival | sector arrival at that country | partial | ⚠ |
| Validity From / To | sector date(s) | partial | ⚠ |
| Urgency / Through | screenshot shows URGENT / Empty | constants? | ⚠ confirm |
| Payment / Quantity | — | — / 1 | ❌ / assume |
| Supplier | — | handling agent per country | ❌ **default agents per country?** |

DG rows (India VOMM-OMDB, Türkiye OMDB-LTFM) also carry: UN1263 / Paint materials / Class 3.

---

## 6. The blocker — services have no API

Checked 3 ways, all agree:

1. **Postman collection** — every parameter of all 25 methods listed; `createFlight`,
   `insertFlights`, `updateFlight` accept **only** `flight{}` + `waypoints[]`. No
   `services` / `permits` key anywhere. ("permit" appears 0 times, "overflight" 0.)
2. **Live API** — `getFlight` returns only `flight` + `waypoints` + `awbs`. Every
   `getServices` / `getFlightServices` / `getServiceList` / `getPermits` →
   *"Method Not Allowed"*.
3. Your allowed-methods list — all are Customer / Flight / AWB CRUD; none is a
   service method.

→ The 11 permit rows **cannot be pushed by API** today.

---

## 7. Questions for the client

**A. Blocker**
1. Is there any API method to create flight **Services / permits**? (e.g.
   `createService`, or a `services[]` array on `createFlight` / `updateFlight`.)
   If not — do permits stay **manual**, or will Awery add one?

**B. Missing values (Flight)**
2. **Operator** for MixJet permit flights — one fixed value, or per mission? What is it?
3. `company__name` = **"MixJet UAE"** for all of these — correct?
4. "**Air Logistics Partners FZE**" is not in the Awery DB. Should the backend
   `createCustomer` automatically, or will your team pre-create customers?

**C. Picklists (send the list or a screenshot of each dropdown)**
5. **Flight type** values
6. **Purpose** values
7. **ACFT type** code for "A330-200F"
8. **Service Type**, **Service Status**, **Schedule status** values

**D. Service rules (once §7-A is answered)**
9. **Ref. No** on a service — what should it contain?
10. **Supplier** per permit — do you keep default handling agents per country, or leave blank?
11. **Status** a new service starts in (Requested / Original / …)?

**E. Data confirmations**
12. Email sector times — always **UTC**? Year shown as `24` → **2024**?
13. Duplicate flight (same callsign + date + route) already in Awery → **skip / update / create new**?
14. Sector payload for legs 1 & 3, MTOW, crew, pax — needed, or leave blank?

---

## 8. What we need back

- Answers to §7 (A–E).
- The picklists (§7-C, §7-D).
- Confirmation the test customer / operator records exist (or permission to create them).

Then: §3 + §4 go live as `createFlight` + `insertFlights`; §5 is built the moment
§7-A gives us a method.

---

## 9. Verified API reference (for the dev)

| Method | Call | Returns |
|---|---|---|
| `getCustomer` | `{ "customer__name": "Hunnu Air" }` | `data.customer` (id, company__name, country…) |
| `getFlightList` | `{ "from_date":"2026-09-04", "to_date":"2026-09-05", "date_type":"departure_date" }` | `data.data_list[]` |
| `getFlight` | `{ "flight_id": 38132 }` (use id, not flight_no) | `data.flight` + `data.waypoints[]` + `data.awbs[]` |
| `createFlight` | `{ "flight": {…}, "waypoints": [ {…} ] }` | `data.flight_id` |
| `insertFlights` | same + `"unique":[0]` to skip dup-check | `data.flight_id` |

Header: `Authorization: Bearer <token>` · `Content-Type: application/json` ·
body `{ "method": "<name>", "params": [ { … } ] }`.
