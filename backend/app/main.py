from contextlib import asynccontextmanager
from app.api.copilot import router as copilot_router
from app.api.documents import router as documents_router

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import app.models
from app.api.ai_intake import router as ai_intake_router
from app.api.complaints import router as complaints_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize database tables when the application starts.

    Alembic migrations will replace create_all in a later version.
    """

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered pharmaceutical customer complaint " "management and QMS assistant."
    ),
    lifespan=lifespan,
)


app.include_router(
    ai_intake_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    complaints_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    documents_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    copilot_router,
    prefix=settings.API_V1_PREFIX,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return a JSON error so API clients never receive an opaque failure."""
    detail = "An unexpected server error occurred."
    if settings.DEBUG:
        detail = f"{type(exc).__name__}: {exc}"

    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


@app.get(
    "/",
    tags=["System"],
)
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "message": "PharmaResolve AI backend is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    database_status = "disconnected"

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            database_status = "connected"
    except Exception:
        database_status = "disconnected"

    return {
        "status": ("healthy" if database_status == "connected" else "degraded"),
        "database": database_status,
        "version": settings.APP_VERSION,
    }


# Keep CORS outside FastAPI's error middleware so even unexpected server
# errors include the CORS headers required by the browser.
app = CORSMiddleware(
    app=app,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
