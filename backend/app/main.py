from contextlib import asynccontextmanager
from .api.copilot import router as copilot_router
from .api.documents import router as documents_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models
from .api.ai_intake import router as ai_intake_router
from .api.complaints import router as complaints_router
from .core.config import settings
from .core.database import Base, SessionLocal, engine


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
