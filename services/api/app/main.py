import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging import configure_logging, new_request_id, request_id_var
from app.routers import admin, auth, chat, emergency, feedback, health, medicine, prescription, providers

configure_logging()
logger = logging.getLogger("medirag")

settings = get_settings()

app = FastAPI(title="MediRAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = new_request_id()
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error for %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our end. Please try again."},
        )
    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("%s %s -> %sms", request.method, request.url.path, latency_ms)
        request_id_var.reset(token)
    response.headers["X-Request-Id"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(medicine.router)
app.include_router(prescription.router)
app.include_router(providers.router)
app.include_router(emergency.router)
app.include_router(feedback.router)
app.include_router(admin.router)
