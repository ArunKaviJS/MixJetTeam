"""Map the AI extraction JSON -> Awery ERP payloads.

The AI part gives us human strings ("Air Logistics Partners FZE", "TC-MAA",
"Chennai International Airport (VOMM)"). Awery API v2 accepts human names/codes
directly via the `<field>__name` convention, so we do NOT need a numeric-id
lookup pass for customer / aircraft / airport here.
"""
from __future__ import annotations

import re
from typing import Any

from dateutil import parser as date_parser


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
_ICAO_RE = re.compile(r"\b([A-Z]{4})\b")


def get(extracted: dict, *keys: str) -> Any:
    """First non-empty value among the given keys (case-insensitive)."""
    lower = {str(k).lower(): v for k, v in extracted.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, "", []):
            return v
    return None


def table_items(extracted: dict, *keys: str) -> list[dict]:
    node = get(extracted, *keys)
    if isinstance(node, dict):
        node = node.get("items")
    return [row for row in node if isinstance(row, dict)] if isinstance(node, list) else []


def icao(value: str | None) -> str | None:
    """'Chennai International Airport (VOMM)' -> 'VOMM'. Falls back to the raw string."""
    if not value:
        return None
    text = str(value).strip()
    m = _ICAO_RE.search(text.upper())
    return m.group(1) if m else text


def norm_dt(value: str | None) -> str | None:
    """Best-effort -> 'YYYY-MM-DD HH:MM:SS'. Returns the raw string if unparseable."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date_parser.parse(text, dayfirst=False, fuzzy=True).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OverflowError, TypeError):
        return text


def _split_regs(primary: str | None, bulk: str | None) -> list[str]:
    out: list[str] = []
    for chunk in [primary or ""] + re.split(r"[,/;|]| and | & ", bulk or ""):
        c = chunk.strip()
        if c and c not in out:
            out.append(c)
    return out


# --------------------------------------------------------------------------- #
# waypoints
# --------------------------------------------------------------------------- #
def build_waypoints(schedule_rows: list[dict], default_call_sign: str | None) -> list[dict]:
    """Flatten schedule legs (From/To pairs) into an ordered Awery waypoint list."""
    points: list[dict] = []

    def add(code: str | None, *, dep: str | None = None, arr: str | None = None,
            call_sign: str | None = None) -> None:
        if not code:
            return
        if points and points[-1]["_icao"] == code:
            if dep:
                points[-1]["planned_departure_date"] = dep
            if arr:
                points[-1]["planned_arrival_date"] = arr
            if call_sign and not points[-1].get("call_sign"):
                points[-1]["call_sign"] = call_sign
            return
        points.append({
            "_icao": code,
            "planned_departure_date": dep,
            "planned_arrival_date": arr,
            "call_sign": call_sign,
        })

    for row in schedule_rows:
        cs = (get(row, "Flight", "Flight No.", "Flight No") or default_call_sign)
        add(icao(get(row, "From")),
            dep=norm_dt(get(row, "Departure", "Departure Time", "ETD")),
            call_sign=cs)
        add(icao(get(row, "To")),
            arr=norm_dt(get(row, "Arrival", "Arrival Time", "ETA")),
            call_sign=cs)

    waypoints: list[dict] = []
    for i, p in enumerate(points, start=1):
        wp: dict[str, Any] = {"prior": i, "actual_origin__name": p["_icao"]}
        if p.get("call_sign"):
            wp["call_sign"] = p["call_sign"]
            if p.get("planned_arrival_date"):
                wp["call_sign_landing"] = p["call_sign"]
        if p.get("planned_departure_date"):
            wp["planned_departure_date"] = p["planned_departure_date"]
        if p.get("planned_arrival_date"):
            wp["planned_arrival_date"] = p["planned_arrival_date"]
        waypoints.append(wp)
    return waypoints


# --------------------------------------------------------------------------- #
# flight
# --------------------------------------------------------------------------- #
def derive_flight_no(schedule_rows: list[dict], override: str | None) -> str | None:
    if override:
        return override
    for row in schedule_rows:
        fn = get(row, "Flight", "Flight No.", "Flight No")
        if fn:
            return str(fn).strip()
    return None


def build_create_flight(
    extracted: dict,
    *,
    company_name: str | None = None,
    flight_no: str | None = None,
    unique: list[Any] | None = None,
) -> dict:
    """Return the single object that goes into params[0] of createFlight / insertFlights."""
    schedule_rows = table_items(extracted, "Flight Schedule")

    customer = get(extracted, "Customer")
    operator = get(extracted, "Operator") or customer
    regs = _split_regs(get(extracted, "Reg No"), get(extracted, "Bulk Reg No"))
    fno = derive_flight_no(schedule_rows, flight_no)

    flight: dict[str, Any] = {
        "status": "planned",
        "payload_unit": "kg",
        "no_follow": 0,
        "positioning": 0,
        "autotrack": 0,
    }
    if customer:
        flight["customer__name"] = customer
    if operator:
        flight["operator__name"] = operator
    if get(extracted, "ACFT Type"):
        flight["actype__name"] = get(extracted, "ACFT Type")
    if regs:
        flight["aircraft__name"] = regs[0]
    if fno:
        flight["flight_no"] = fno
    if get(extracted, "Purposes"):
        flight["purpose__name"] = get(extracted, "Purposes")
    if get(extracted, "Flight Type"):
        flight["flight_type"] = str(get(extracted, "Flight Type")).lower()
    if company_name:
        flight["company__name"] = company_name

    payload: dict[str, Any] = {
        "flight": flight,
        "waypoints": build_waypoints(schedule_rows, fno),
    }
    if unique is not None:
        payload["unique"] = unique

    # Carry the permit/sector rows through untouched so the caller / frontend can
    # still see them (Awery service creation is a separate, not-yet-wired step).
    permits = table_items(extracted, "Flight Sectors")
    if permits:
        payload["_permits_preview"] = permits
    return payload


def build_create_customer(extracted: dict, *, company_name: str | None = None) -> dict:
    name = get(extracted, "Customer")
    customer: dict[str, Any] = {"customer_name": name, "auto_customer_code": True}
    if company_name:
        customer["company__name"] = company_name
    return {"customer": customer}
