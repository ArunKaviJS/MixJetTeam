"""File list / detail / update / proceed — everything the React frontend needs.

Reads the AI pipeline's Mongo documents and, on Proceed, runs the Awery flow and
writes the outcome back onto the same document under `awery`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .. import awery_client, config, db, mappers
from ..schemas import FileUpdate, ProceedRequest

router = APIRouter(prefix="/files", tags=["files"])


def _cluster_filter() -> dict:
    """Scope queries to Aviation Permit Request documents only."""
    if not config.AVIATION_CLUSTER_ID:
        return {}
    try:
        return {"clusterId": db.to_object_id(config.AVIATION_CLUSTER_ID)}
    except ValueError:
        return {"clusterId": config.AVIATION_CLUSTER_ID}

# Scalar fields shown in the list "Extracted_results" column, in order.
_SUMMARY_KEYS = [
    "Customer", "Operator", "Purposes", "Flight Type",
    "Reg No", "ACFT Type", "Bulk Reg No",
]


def _extracted(doc: dict) -> dict:
    """Backend ALWAYS works from `updatedExtractedValues` only.

    `extractedValues` is the untouched original the AI wrote — kept purely as a log.
    It is never read for mapping/summary and never modified by this service.
    """
    ev = doc.get("updatedExtractedValues")
    return ev if isinstance(ev, dict) else {}


def _summary(doc: dict) -> str:
    ev = _extracted(doc)
    parts = []
    for key in _SUMMARY_KEYS:
        val = ev.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    return " | ".join(parts)


def _list_item(doc: dict) -> dict:
    awery = doc.get("awery") or {}
    return {
        "id": str(doc["_id"]),
        "file_name": doc.get("fileName") or "",
        "status": doc.get("processingStatus") or doc.get("status") or "",
        "uploaded_at": doc.get("createdAt") or "",
        "extracted_summary": _summary(doc),
        "original_file": doc.get("originalFile") or "",
        "awery_status": awery.get("status"),
        "awery_flight_id": awery.get("flight_id"),
    }


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #
@router.get("")
def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="matches fileName or customer name"),
) -> dict:
    if not db.available():
        raise HTTPException(503, "MONGO_URI is not configured in awery-backend/.env")

    col = db.files()
    query: dict[str, Any] = _cluster_filter()
    if search:
        rx = {"$regex": search.strip(), "$options": "i"}
        query = {**query, "$or": [
            {"fileName": rx},
            {"updatedExtractedValues.Customer": rx},
        ]}

    total = col.count_documents(query)
    cursor = (
        col.find(query)
        .sort("_id", db.DESCENDING)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_list_item(d) for d in cursor]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# --------------------------------------------------------------------------- #
# detail
# --------------------------------------------------------------------------- #
@router.get("/{file_id}")
def get_file(file_id: str) -> dict:
    if not db.available():
        raise HTTPException(503, "MONGO_URI is not configured in awery-backend/.env")
    try:
        oid = db.to_object_id(file_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    doc = db.files().find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, f"No file with id {file_id}")
    return db.jsonable(doc)


# --------------------------------------------------------------------------- #
# update edited extraction values (the "Update" button)
# --------------------------------------------------------------------------- #
@router.put("/{file_id}")
def update_file(file_id: str, body: FileUpdate) -> dict:
    if not db.available():
        raise HTTPException(503, "MONGO_URI is not configured in awery-backend/.env")
    try:
        oid = db.to_object_id(file_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    res = db.files().update_one(
        {"_id": oid},
        {"$set": {
            "updatedExtractedValues": body.updatedExtractedValues,
            "updatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(404, f"No file with id {file_id}")
    return db.jsonable(db.files().find_one({"_id": oid}))


# --------------------------------------------------------------------------- #
# delete (removes the app's own Mongo document only — never touches Awery)
# --------------------------------------------------------------------------- #
@router.delete("/{file_id}")
def delete_file(file_id: str) -> dict:
    if not db.available():
        raise HTTPException(503, "MONGO_URI is not configured in awery-backend/.env")
    try:
        oid = db.to_object_id(file_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    res = db.files().delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, f"No file with id {file_id}")
    return {"deleted": file_id}


# --------------------------------------------------------------------------- #
# PROCEED  -> Awery ERP
# --------------------------------------------------------------------------- #
@router.post("/{file_id}/proceed")
def proceed(file_id: str, body: ProceedRequest | None = None) -> dict:
    """Frontend 'Proceed' button: extraction -> Awery createFlight -> store result."""
    body = body or ProceedRequest()
    if not db.available():
        raise HTTPException(503, "MONGO_URI is not configured in awery-backend/.env")
    try:
        oid = db.to_object_id(file_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    doc = db.files().find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, f"No file with id {file_id}")

    extracted = _extracted(doc)
    if not extracted:
        raise HTTPException(422, "This file has no `updatedExtractedValues` to send")

    flight_payload = mappers.build_create_flight(
        extracted,
        company_name=body.company_name,
        flight_no=body.flight_no,
        unique=body.unique,
    )
    wire = {k: v for k, v in flight_payload.items() if not k.startswith("_")}

    result: dict[str, Any] = {
        "file_id": file_id,
        "dry_run": body.dry_run,
        "sent_payload": flight_payload,
    }

    if body.dry_run:
        if body.create_customer:
            result["create_customer_payload"] = mappers.build_create_customer(
                extracted, company_name=body.company_name
            )
        return result

    awery_record: dict[str, Any] = {
        "status": "pending",
        "sent_payload": wire,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }

    try:
        if body.create_customer:
            cust_params = mappers.build_create_customer(extracted, company_name=body.company_name)
            awery_record["create_customer_response"] = awery_client.call("createCustomer", cust_params)

        envelope = awery_client.call("createFlight", wire)
        data = envelope.get("data") or {}
        awery_record.update({
            "status": "created",
            "flight_id": data.get("flight_id"),
            "flight_no": wire["flight"].get("flight_no"),
            "response": envelope,
            "error": None,
        })
    except awery_client.AweryError as exc:
        awery_record.update({
            "status": "failed",
            "error": exc.message,
            "response": {"data": exc.data, "http_status": exc.http_status},
        })

    db.files().update_one({"_id": oid}, {"$set": {"awery": awery_record}})

    result["awery"] = awery_record
    if awery_record["status"] == "failed":
        raise HTTPException(502, {"message": awery_record["error"], "awery": db.jsonable(awery_record)})
    return db.jsonable(result)
