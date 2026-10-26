"""POST endpoints. Triggered by the React frontend once the AI part is done.

Flow for POST /awery/process:
    AI extraction JSON  ->  mappers.build_create_flight  ->  Awery createFlight
    (optionally Awery createCustomer first)

update* / delete* methods are deliberately NOT exposed.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from .. import awery_client, config, db, mappers
from ..schemas import CreateCustomerRequest, ProcessRequest, RpcRequest

router = APIRouter(prefix="/awery", tags=["awery-write"])


def _call(method: str, params: dict) -> dict:
    try:
        return awery_client.call(method, params)
    except awery_client.AweryError as exc:
        raise HTTPException(
            status_code=exc.http_status or 502,
            detail={"message": exc.message, "data": exc.data, "sent": exc.request_body},
        )


def _load_from_mongo(mongo_id: str) -> dict:
    if not db.available():
        raise HTTPException(400, "mongo_id given but MONGO_URI is not configured in .env")
    try:
        oid = db.to_object_id(mongo_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    doc = db.files().find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, f"No {config.FILE_DETAILS} doc with _id={mongo_id}")
    extracted = doc.get("updatedExtractedValues")
    if not isinstance(extracted, dict):
        raise HTTPException(422, "Mongo doc has no `updatedExtractedValues` object")
    return extracted


@router.post("/customer")
def create_customer(body: CreateCustomerRequest) -> dict:
    """Awery `createCustomer`. Body maps straight to params[0]."""
    params = body.model_dump(exclude_none=True)
    return _call("createCustomer", params)


@router.post("/flight")
def create_flight(payload: dict[str, Any]) -> dict:
    """Awery `createFlight`. Body must be the params[0] object: {"flight": {...}, "waypoints": [...]}."""
    if "flight" not in payload:
        raise HTTPException(422, 'Body must contain a "flight" object')
    return _call("createFlight", payload)


@router.post("/flights/insert")
def insert_flights(payload: dict[str, Any]) -> dict:
    """Awery `insertFlights` (bulk create/update). Body = params[0] object."""
    if "flight" not in payload and "flights" not in payload:
        raise HTTPException(422, 'Body must contain a "flight" object')
    return _call("insertFlights", payload)


@router.post("/rpc")
def rpc_passthrough(body: RpcRequest) -> dict:
    """Thin passthrough, restricted to config.ALLOWED_METHODS. Handy for Postman."""
    if body.method not in config.ALLOWED_METHODS:
        raise HTTPException(403, f"Method '{body.method}' is not allowed")
    return _call(body.method, body.params)


@router.post("/process")
def process(body: ProcessRequest) -> dict:
    """Main entry point for the frontend click: AI extraction -> Awery flight."""
    if not body.extracted and not body.mongo_id:
        raise HTTPException(422, "Provide either `extracted` or `mongo_id`")

    extracted = body.extracted or _load_from_mongo(body.mongo_id)  # type: ignore[arg-type]

    flight_payload = mappers.build_create_flight(
        extracted,
        company_name=body.company_name,
        flight_no=body.flight_no,
        unique=body.unique,
    )

    result: dict[str, Any] = {
        "dry_run": body.dry_run,
        "create_flight_payload": flight_payload,
    }

    if body.dry_run:
        if body.create_customer:
            result["create_customer_payload"] = mappers.build_create_customer(
                extracted, company_name=body.company_name
            )
        return result

    if body.create_customer:
        cust_params = mappers.build_create_customer(extracted, company_name=body.company_name)
        result["create_customer_payload"] = cust_params
        result["create_customer_response"] = _call("createCustomer", cust_params)

    # Awery ignores unknown keys, but keep our preview out of the wire payload.
    wire = {k: v for k, v in flight_payload.items() if not k.startswith("_")}
    result["create_flight_response"] = _call("createFlight", wire)

    data = result["create_flight_response"].get("data") or {}
    result["flight_id"] = data.get("flight_id")
    return result
