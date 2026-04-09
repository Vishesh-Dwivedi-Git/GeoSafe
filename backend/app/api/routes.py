"""
FastAPI routes for the AI-first GeoSafe backend.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.schemas.schemas import AnalyzeLandResponse, HealthResponse, ValidationRequest
from app.services.analyze_service import analyze_service
from app.services.geocoding import GeocodingService
from app.services.kgis_fetch import KGISFetchService
from app.services.kgis_webapi import KGISWebAPIService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1", tags=["GeoSafe"])

geocoding_service = GeocodingService()
kgis_service = KGISWebAPIService()
layer_fetch_service = KGISFetchService()


async def _db_connected() -> bool:
    if not settings.ENABLE_DATABASE:
        logger.info("Database checks disabled; treating DB as optional for this deployment")
        return True
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False


async def _kgis_reachable() -> bool:
    try:
        data = await kgis_service.location_details(12.9716, 77.5946, aoi="w")
        return bool((data or {}).get("Count") or (data or {}).get("value"))
    except Exception as exc:
        logger.warning("KGIS health check failed: %s", exc)
        return False


def _to_payload(request: ValidationRequest) -> dict[str, Any]:
    return {
        "input_type": request.input_type,
        "survey_input": request.survey_input.model_dump() if request.survey_input else None,
        "coordinates_input": request.coordinates_input.model_dump() if request.coordinates_input else None,
    }


def _validate_request_shape(request: ValidationRequest) -> None:
    if request.input_type == "survey_number" and not request.survey_input:
        raise HTTPException(status_code=422, detail="survey_input is required for survey_number requests")
    if request.input_type == "coordinates" and not request.coordinates_input:
        raise HTTPException(status_code=422, detail="coordinates_input is required for coordinates requests")


async def _run_analysis(request: ValidationRequest) -> AnalyzeLandResponse:
    _validate_request_shape(request)
    try:
        result = await analyze_service.analyze(_to_payload(request))
        return AnalyzeLandResponse(
            risk=result.risk,
            confidence=result.confidence,
            features=result.features,
            reasoning=result.reasoning,
            bhuvan_hits=result.bhuvan_hits,
            centroid_lat=result.centroid_lat,
            centroid_lon=result.centroid_lon,
            area_sqm=result.area_sqm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI land analysis failed")
        raise HTTPException(status_code=500, detail=f"AI land analysis failed: {exc}") from exc


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        version=settings.APP_VERSION,
        db_connected=await _db_connected(),
        kgis_reachable=await _kgis_reachable(),
    )


@router.post("/geocode")
async def geocode(request: ValidationRequest) -> dict[str, Any]:
    _validate_request_shape(request)

    if request.input_type == "survey_number":
        result = await geocoding_service.resolve(
            input_type="survey_number",
            survey_input=request.survey_input.model_dump(),
        )
    else:
        result = await geocoding_service.resolve(
            input_type="coordinates",
            coordinates_input=request.coordinates_input.model_dump(),
        )

    return {
        "input_type": request.input_type,
        "raw_input": result.raw_input,
        "centroid_lat": result.centroid_lat,
        "centroid_lon": result.centroid_lon,
        "area_sqm": round(result.area_sqm, 2),
        "source": result.source,
        "confidence": result.confidence,
        "boundary_geojson": result.to_geojson(),
    }


@router.post("/analyze-land", response_model=AnalyzeLandResponse)
async def analyze_land(request: ValidationRequest) -> AnalyzeLandResponse:
    return await _run_analysis(request)


@router.post("/validate", response_model=AnalyzeLandResponse)
async def validate(request: ValidationRequest) -> AnalyzeLandResponse:
    """
    Backward-compatible analysis endpoint.
    The backend now routes validation through the AI-first pipeline.
    """
    return await _run_analysis(request)


@router.get("/layers")
async def layers() -> dict[str, Any]:
    layers = layer_fetch_service.layers
    return {
        "layers": [
            {
                "layer_name": name,
                "label": cfg["label"],
                "buffer_m": cfg["buffer_m"],
                "configured": bool(
                    cfg.get("geojson_path")
                    or cfg.get("geojson_url")
                    or cfg.get("nearby_asset_code")
                ),
                "preferred_source": (
                    "geojson_file"
                    if cfg.get("geojson_path")
                    else "geojson_url"
                    if cfg.get("geojson_url")
                    else "nearby_assets"
                    if cfg.get("nearby_asset_code")
                    else "unconfigured"
                ),
            }
            for name, cfg in layers.items()
        ]
    }
