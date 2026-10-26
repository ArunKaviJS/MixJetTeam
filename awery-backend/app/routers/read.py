"""GET endpoints for checking Awery data from Postman / the browser.

These are the "check with GET methods" the integration doc asks for. They map
1:1 onto Awery read methods and return the raw Awery envelope.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .. import awery_client

router = APIRouter(prefix="/awery", tags=["awery-read"])


def _call(method: str, params: dict) -> dict:
    try:
        return awery_client.call(method, params)
    except awery_client.AweryError as exc:
        raise HTTPException(
            status_code=exc.http_status or 502,
            detail={"message": exc.message, "data": exc.data, "sent": exc.request_body},
        )


@router.get("/customer")
def get_customer(
    id: int | None = Query(default=None, description="Awery inner customer id"),
    customer_code: str | None = Query(default=None),
    slx_id: str | None = Query(default=None),
    company_code: str | None = Query(default=None),
) -> dict:
    """Awery `getCustomer` — one of id | customer_code | slx_id is required."""
    params: dict[str, Any] = {}
    if id is not None:
        params["id"] = id
    if customer_code:
        params["customer_code"] = customer_code
    if slx_id:
        params["slx_id"] = slx_id
    if company_code:
        params["company_code"] = company_code
    if not params:
        raise HTTPException(422, "Provide id, customer_code or slx_id")
    return _call("getCustomer", params)


@router.get("/flight")
def get_flight(
    flight_id: int | None = Query(default=None),
    flight_no: str | None = Query(default=None, description="e.g. MIX22985"),
    slx_id: str | None = Query(default=None),
) -> dict:
    """Awery `getFlight` — one of flight_id | flight_no | slx_id is required."""
    params: dict[str, Any] = {}
    if flight_id is not None:
        params["flight_id"] = flight_id
    if flight_no:
        params["flight_no"] = flight_no
    if slx_id:
        params["slx_id"] = slx_id
    if not params:
        raise HTTPException(422, "Provide flight_id, flight_no or slx_id")
    return _call("getFlight", params)


@router.get("/flight-list")
def get_flight_list(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    date_type: str = Query("departure_date"),
) -> dict:
    """Awery `getFlightList` — flights within a period."""
    return _call(
        "getFlightList",
        {"from_date": from_date, "to_date": to_date, "date_type": date_type},
    )


@router.get("/flights")
def get_flights(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    flight_no: str | None = Query(default=None),
) -> dict:
    """Awery `getFlights` (allowed method; params passed through as given)."""
    params: dict[str, Any] = {}
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    if flight_no:
        params["flight_no"] = flight_no
    return _call("getFlights", params)
