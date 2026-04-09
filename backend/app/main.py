"""
GeoSafe FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.services.layer_service import LayerService
from app.services.ml_service import ml_service

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("geosafe")
layer_service = LayerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GeoSafe API starting")
    logger.info("Version : %s", settings.APP_VERSION)
    logger.info("Debug   : %s", settings.DEBUG)
    logger.info("LLM     : %s / %s", settings.LLM_PROVIDER, settings.LLM_MODEL)
    logger.info("Database optional mode: %s", not settings.ENABLE_DATABASE)
    ml_service.load()
    await layer_service.initialize()
    yield
    logger.info("GeoSafe API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "GeoSafe provides KGIS-backed parcel resolution and AI-powered "
        "geospatial land risk analysis for Karnataka."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api/v1",
    }
