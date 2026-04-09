"""
GeoSafe configuration loaded from environment variables via .env.
"""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GeoSafe API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    USE_DEMO_DATA: bool = True
    SECRET_KEY: str = "change-me-in-production"
    ENABLE_DATABASE: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/geosafe"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/geosafe"

    # Single geospatial source of truth: KGIS Web APIs.
    KGIS_WFS_BASE_URL: str = "https://kgis.ksrsac.in/kgis/ows"
    KGIS_WMS_BASE_URL: str = "https://kgis.ksrsac.in/kgis/wms"
    KGIS_DATA_SOURCE_MODE: str = "webapi"
    KGIS_WEBAPI_BASE_URL: str = "https://kgis.ksrsac.in:9000/genericwebservices/ws"
    KGIS_NEARBY_ASSETS_BASE_URL: str = "https://kgis.ksrsac.in:9000/NearbyAssets/ws"
    KGIS_API_KEY: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_WATER_BODIES: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_FOREST: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_ECO_SENSITIVE: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_FLOOD: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_GOVT_LAND: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_REVENUE_LAND: Optional[str] = None
    KGIS_LAYER_WATER_BODIES_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_WATER_BODIES_GEOJSON_URL: Optional[str] = None
    KGIS_LAYER_FOREST_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_FOREST_GEOJSON_URL: Optional[str] = None
    KGIS_LAYER_ECO_SENSITIVE_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_ECO_SENSITIVE_GEOJSON_URL: Optional[str] = None
    KGIS_LAYER_FLOOD_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_FLOOD_GEOJSON_URL: Optional[str] = None
    KGIS_LAYER_GOVT_LAND_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_GOVT_LAND_GEOJSON_URL: Optional[str] = None
    KGIS_LAYER_REVENUE_LAND_GEOJSON_PATH: Optional[str] = None
    KGIS_LAYER_REVENUE_LAND_GEOJSON_URL: Optional[str] = None
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    BHUVAN_FOREST_WMS_URL: Optional[str] = None
    BHUVAN_FOREST_LAYER_NAME: Optional[str] = None
    BHUVAN_ESZ_WMS_URL: Optional[str] = None
    BHUVAN_ESZ_LAYER_NAME: Optional[str] = None
    BHUVAN_FLOOD_WMS_URL: Optional[str] = None
    BHUVAN_FLOOD_LAYER_NAME: Optional[str] = None
    BHUVAN_GOVT_LAND_WMS_URL: Optional[str] = None
    BHUVAN_GOVT_LAND_LAYER_NAME: Optional[str] = None
    GIS_LAYER_CACHE_TTL_SECONDS: int = 900
    ANALYZE_BUFFER_M: float = 500.0
    FALLBACK_POINTS_PATH: str = "data/fallback_points.json"
    FALLBACK_POINT_RADIUS_M: float = 2500.0
    ENABLE_KARNATAKA_HEURISTIC_FALLBACK: bool = True

    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-1.5-flash"

    AI_MODEL_PATH: str = "../ml/model.pkl"
    AI_LABEL_ENCODER_PATH: str = "../ml/label_encoder.pkl"
    ML_MODEL_PATH: str = "ml/models/risk_classifier.pkl"
    SHAP_EXPLAINER_PATH: str = "ml/models/shap_explainer.pkl"
    LABEL_ENCODER_PATH: str = "ml/models/label_encoder.pkl"

    BHUNAKSHA_BASE_URL: str = "https://bhunaksha.karnataka.gov.in"
    DHARITRI_BASE_URL: str = "https://landrecords.karnataka.gov.in"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"

    REPORTS_DIR: str = "reports"
    MAPBOX_TOKEN: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    FROM_EMAIL: str = "noreply@geosafe.in"

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
