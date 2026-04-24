import logging
from fastapi import FastAPI

from app.config.logging import configure_logging
from app.routes.chatRoute import router as chat_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="AI System API")

app.include_router(chat_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI server is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
