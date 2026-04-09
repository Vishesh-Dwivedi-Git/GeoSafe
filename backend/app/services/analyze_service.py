"""
End-to-end AI land analysis orchestration.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.services.explainer import explainer_service
from app.services.feature_extractor import FeatureExtractor
from app.services.kgis_service import KGISService
from app.services.layer_service import LayerService
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)


@dataclass
class AnalyzeLandResult:
    risk: str
    confidence: float
    features: dict[str, float]
    reasoning: list[str]
    bhuvan_hits: dict[str, bool]
    source: str
    raw_input: str
    centroid_lat: float
    centroid_lon: float
    area_sqm: float

def _apply_rule_override(predicted_risk: str, features: dict[str, float]) -> str:
    if features.get("esz_present", 0.0) >= 1.0:
        return "HIGH"
    if features.get("forest_present", 0.0) >= 1.0:
        return "HIGH"
    return predicted_risk


class AnalyzeService:
    """Primary application service for AI-based land analysis."""

    def __init__(self):
        self._kgis = KGISService()
        self._layers = LayerService()
        self._feature_extractor = FeatureExtractor()

    async def analyze(self, payload: dict[str, Any]) -> AnalyzeLandResult:
        logger.info("Starting AI land analysis for input_type=%s", payload.get("input_type"))
        land = await self._kgis.resolve_land(payload)
        logger.info(
            "Resolved land geometry source=%s centroid=(%.6f, %.6f) area=%.2f",
            land.source,
            land.centroid_lat,
            land.centroid_lon,
            land.area_sqm,
        )
        layers = await self._layers.get_layers(land.centroid_lat, land.centroid_lon, 500.0)
        features = self._feature_extractor.extract(
            {"lat": land.centroid_lat, "lng": land.centroid_lon},
            layers,
        )
        prediction = ml_service.predict(features)
        final_risk = _apply_rule_override(prediction.risk, features)
        reasoning = explainer_service.explain(features, final_risk)
        logger.info(
            "Prediction complete model_risk=%s final_risk=%s confidence=%.4f",
            prediction.risk,
            final_risk,
            prediction.confidence,
        )

        return AnalyzeLandResult(
            risk=final_risk,
            confidence=round(prediction.confidence, 4),
            features={key: round(float(value), 4) for key, value in features.items()},
            reasoning=reasoning,
            bhuvan_hits={
                "forest": bool((layers.get("forest") or {}).get("present")),
                "esz": bool((layers.get("esz") or {}).get("present")),
                "flood": bool((layers.get("flood") or {}).get("present")),
            },
            source=land.source,
            raw_input=land.raw_input,
            centroid_lat=land.centroid_lat,
            centroid_lon=land.centroid_lon,
            area_sqm=round(land.area_sqm, 2),
        )


analyze_service = AnalyzeService()
