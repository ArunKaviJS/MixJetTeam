from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import files, health, read, write

app = FastAPI(
    title="MixJet · Awery ERP Backend",
    version="0.1.0",
    description=(
        "Bridges the AI extraction output to the Awery ERP API v2 (HTTP over jRPC, "
        "single endpoint /rpc/json/). GET endpoints are for checking data; "
        "POST /awery/process is the frontend trigger. No update/delete methods."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.AWERY_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(files.router)
app.include_router(read.router)
app.include_router(write.router)


@app.get("/")
def root() -> dict:
    return {"service": "awery-backend", "docs": "/docs", "health": "/health"}
