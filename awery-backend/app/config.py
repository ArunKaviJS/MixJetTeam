import os

from dotenv import load_dotenv

load_dotenv()


def _clean(value: str | None) -> str:
    return (value or "").strip()


# ---- Awery ERP API ----
AWERY_ERP_API_URL = _clean(os.getenv("AWERY_ERP_API_URL")) or "https://mixjetdev.awery.com/rpc/json/"
AWERY_ERP_API_BEARER_TOKEN = _clean(os.getenv("AWERY_ERP_API_BEARER_TOKEN"))
AWERY_AUTH_SCHEME = (_clean(os.getenv("AWERY_AUTH_SCHEME")) or "bearer").lower()
AWERY_REQUEST_TIMEOUT = float(_clean(os.getenv("AWERY_REQUEST_TIMEOUT")) or "30")

# ---- This service ----
AWERY_BACKEND_HOST = _clean(os.getenv("AWERY_BACKEND_HOST")) or "0.0.0.0"
AWERY_BACKEND_PORT = int(_clean(os.getenv("AWERY_BACKEND_PORT")) or "8200")

def _origin(o: str) -> str:
    # Browsers send Origin without a trailing slash/path — strip one if pasted in.
    return o.strip().rstrip("/")


_cors = _clean(os.getenv("AWERY_CORS_ORIGINS")) or "*"
AWERY_CORS_ORIGINS = ["*"] if _cors == "*" else [_origin(o) for o in _cors.split(",") if o.strip()]

# ---- Optional Mongo (shared with ../ai) ----
MONGO_URI = _clean(os.getenv("MONGO_URI"))
DB_NAME = _clean(os.getenv("DB_NAME")) or "yellow_chunks"
FILE_DETAILS = _clean(os.getenv("FILE_DETAILS")) or "tb_file_details"

# The AI pipeline tags every "Aviation Permit Request" document with this clusterId
# (see ../ai/gmailmongo.py). The file list is scoped to it so shared-DB noise from
# other products is filtered out. Set to "" to show every document.
AVIATION_CLUSTER_ID = _clean(os.getenv("AVIATION_CLUSTER_ID")) or "693901f09d8dbf36a427bd91"

# Methods this backend is allowed to call on Awery.
# NOTE: update* / delete* are intentionally excluded for now.
ALLOWED_METHODS = {
    "getFlight",
    "getFlights",
    "getFlightList",
    "getCustomer",
    "createFlight",
    "insertFlights",
    "createCustomer",
}

READ_METHODS = {"getFlight", "getFlights", "getFlightList", "getCustomer"}
