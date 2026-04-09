"""
High-level KGIS integration service for AI land analysis.
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.geocoding import GeocodingResult, GeocodingService

settings = get_settings()


class KGISService:
    """Resolve user input into parcel geometry while preserving existing KGIS-backed flow."""

    def __init__(self):
        self._geocoding = GeocodingService()

    async def resolve_land(self, payload: dict[str, Any]) -> GeocodingResult:
        input_type = payload["input_type"]
        if input_type == "survey_number":
            return await self._geocoding.resolve(
                input_type="survey_number",
                survey_input=payload.get("survey_input") or {},
            )
        return await self._geocoding.resolve(
            input_type="coordinates",
            coordinates_input=payload.get("coordinates_input")
            or {
                "latitude": payload["coordinates_input"]["latitude"],
                "longitude": payload["coordinates_input"]["longitude"],
                "buffer_m": payload["coordinates_input"].get("buffer_m", settings.ANALYZE_BUFFER_M),
            },
        )
