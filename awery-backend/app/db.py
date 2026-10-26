"""MongoDB access — the same DB the AI part (../ai/gmailmongo.py) writes to.

The AI pipeline stores one document per processed email in
`<DB_NAME>.<FILE_DETAILS>` (default: yellow_chunks.tb_file_details):

    {
      "_id": ObjectId,
      "fileName": "Email_20260818_122632_564576_merged",
      "processingStatus": "Completed",
      "originalFile": "https://.../Email_..._merged.pdf",   # PDF for the preview pane
      "originalS3File": "uploads/Email_..._merged.pdf",
      "extractedValues":        { ...AI output... },          # original
      "updatedExtractedValues": { ...AI output... },          # user-edited copy
      "createdAt": "2026-08-18T12:26:32.564Z",
      "awery": { ... }                                        # <- added by this backend on Proceed
    }
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection

from . import config

_client: MongoClient | None = None


def available() -> bool:
    return bool(config.MONGO_URI)


def files() -> Collection:
    global _client
    if not config.MONGO_URI:
        raise RuntimeError("MONGO_URI is not configured in awery-backend/.env")
    if _client is None:
        _client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=8000)
    return _client[config.DB_NAME][config.FILE_DETAILS]


def to_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise ValueError(f"'{value}' is not a valid Mongo id") from exc


def jsonable(value: Any) -> Any:
    """Recursively turn a Mongo document into plain JSON-safe types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    return value


__all__ = ["available", "files", "to_object_id", "jsonable", "DESCENDING"]
