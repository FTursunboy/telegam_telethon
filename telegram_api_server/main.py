import time

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from telegram_api_server.api.routes import router
from telegram_api_server.core.errors import register_error_handlers
from telegram_api_server.core.logging import setup_logging
from telegram_api_server.core.metrics import api_request_duration_seconds

setup_logging()
app = FastAPI(title="Telegram API Server Management (Python)", version="0.1.0")
register_error_handlers(app)
app.include_router(router)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - started
    api_request_duration_seconds.labels(path=request.url.path).observe(duration)
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
