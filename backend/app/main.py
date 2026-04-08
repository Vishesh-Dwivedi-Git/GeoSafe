"""
GeoSafe — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router

settings = get_settings()

# ── Logging ───────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("geosafe")


# ── Lifespan (startup / shutdown) ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━━━ GeoSafe API starting ━━━")
    logger.info("Version : %s", settings.APP_VERSION)
    logger.info("Debug   : %s", settings.DEBUG)
    logger.info("LLM     : %s / %s", settings.LLM_PROVIDER, settings.LLM_MODEL)
    yield
    logger.info("━━━ GeoSafe API shutting down ━━━")


# ── FastAPI App ───────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**GeoSafe** — AI-powered land safety validation for Karnataka, India.\n\n"
        "Automatically retrieves KGIS layers, performs multi-layer spatial validation "
        "against water bodies, forests, eco-sensitive zones, and government lands, "
        "then generates a comprehensive safety report with legal citations and "
        "plain-language explanations.\n\n"
        "### Flow Architecture\n"
        "1. **Geocoding** — Survey number / coordinates → boundary polygon\n"
        "2. **KGIS Fetch** — Auto-retrieve water bodies, forest, ESZ, flood, govt layers\n"
        "3. **Spatial Validation** — PostGIS-style intersection, overlap %, buffer checks\n"
        "4. **Risk Classifier** — Random Forest + SHAP feature importance\n"
        "5. **Flag Mapping** — Karnataka act citations + severity levels\n"
        "6. **LLM Explainability** — Plain-language summary via Gemini/OpenAI\n"
        "7. **Report Generation** — Risk badge, flags, map overlay, next steps\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────
app.include_router(router)


# ── Root redirect ─────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api/v1",
    }
