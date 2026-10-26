"""Low-level client for the Awery ERP API v2 (HTTP over jRPC).

Everything goes to a single endpoint (AWERY_ERP_API_URL) as:

    POST /rpc/json/
    Authorization: Bearer <token>
    Content-Type: application/json

    { "method": "<method>", "params": [ { ...one object... } ] }

Response envelope:

    { "jsonrpc": ..., "status": true|false, "message": "...",
      "data": <payload|null>, "suspend": false, "id": ... }
"""
from __future__ import annotations

from typing import Any

import requests

from . import config


class AweryError(RuntimeError):
    """Raised when Awery returns status=false or a transport/HTTP error."""

    def __init__(self, message: str, *, http_status: int | None = None,
                 data: Any = None, request_body: Any = None):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.data = data
        self.request_body = request_body


def _auth_header() -> dict[str, str]:
    token = config.AWERY_ERP_API_BEARER_TOKEN
    if not token:
        raise AweryError(
            "AWERY_ERP_API_BEARER_TOKEN is not set. Add it to awery-backend/.env"
        )
    if config.AWERY_AUTH_SCHEME == "raw":
        return {"Authorization": token}
    return {"Authorization": f"Bearer {token}"}


def call(method: str, params: dict | None = None) -> dict:
    """Call an Awery method with a single params object. Returns the full envelope."""
    if method not in config.ALLOWED_METHODS:
        raise AweryError(f"Method '{method}' is not allowed by this backend")

    body = {"method": method, "params": [params or {}]}
    headers = {"Content-Type": "application/json", **_auth_header()}

    try:
        resp = requests.post(
            config.AWERY_ERP_API_URL,
            json=body,
            headers=headers,
            timeout=config.AWERY_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:  # network / DNS / timeout
        raise AweryError(f"Could not reach Awery: {exc}", request_body=body) from exc

    try:
        envelope = resp.json()
    except ValueError:
        raise AweryError(
            f"Awery returned non-JSON (HTTP {resp.status_code}): {resp.text[:500]}",
            http_status=resp.status_code,
            request_body=body,
        )

    if isinstance(envelope, dict) and envelope.get("status") is False:
        raise AweryError(
            envelope.get("message") or "Awery returned status=false",
            http_status=resp.status_code,
            data=envelope.get("data"),
            request_body=body,
        )

    if not resp.ok:
        raise AweryError(
            f"Awery HTTP {resp.status_code}: {resp.text[:500]}",
            http_status=resp.status_code,
            request_body=body,
        )

    return envelope
