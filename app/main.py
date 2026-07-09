from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import RequestResponseEndpoint

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import Delivery, DeliveryEvent, HandoffOffer, OutboxEvent, User  # noqa: F401

settings = get_settings()
REQUESTS = Counter("relayroute_http_requests_total", "HTTP requests", ["method", "path", "status"])
DURATION = Histogram(
    "relayroute_http_request_duration_seconds", "HTTP duration", ["method", "path"]
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Real-time delivery tracking, relay handoffs, geospatial presence, and chat.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started = perf_counter()
    response = await call_next(request)
    path = request.url.path
    REQUESTS.labels(request.method, path, response.status_code).inc()
    DURATION.labels(request.method, path).observe(perf_counter() - started)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": __version__, "docs": "/docs"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router)
