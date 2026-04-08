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

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/geosafe"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/geosafe"

    # Single geospatial source of truth: KGIS Web APIs.
    KGIS_WEBAPI_BASE_URL: str = "https://kgis.ksrsac.in:9000/genericwebservices/ws"
    KGIS_NEARBY_ASSETS_BASE_URL: str = "https://kgis.ksrsac.in:9000/NearbyAssets/ws"
    KGIS_API_KEY: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_WATER_BODIES: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_FOREST: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_ECO_SENSITIVE: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_FLOOD: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_GOVT_LAND: Optional[str] = None
    KGIS_NEARBY_ASSET_CODE_REVENUE_LAND: Optional[str] = None

    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-1.5-flash"

    ML_MODEL_PATH: str = "ml/models/risk_classifier.pkl"
    SHAP_EXPLAINER_PATH: str = "ml/models/shap_explainer.pkl"
    LABEL_ENCODER_PATH: str = "ml/models/label_encoder.pkl"

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
