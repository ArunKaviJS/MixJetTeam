"""Start the Awery backend on its own port (default 8200)."""
import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.AWERY_BACKEND_HOST,
        port=config.AWERY_BACKEND_PORT,
        reload=True,
    )
