from fastapi import APIRouter

from .. import config

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "service": "awery-backend",
        "ok": True,
        "awery_url": config.AWERY_ERP_API_URL,
        "token_configured": bool(config.AWERY_ERP_API_BEARER_TOKEN),
        "auth_scheme": config.AWERY_AUTH_SCHEME,
        "allowed_methods": sorted(config.ALLOWED_METHODS),
    }
