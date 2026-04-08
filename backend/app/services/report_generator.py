"""
Step 7 — Safety Report Generation & Export

Orchestrates the full pipeline and produces the final report.
Also handles PDF export and shareable link generation.
"""
import logging
import time
import uuid
import secrets
from typing import Optional
from io import BytesIO
from datetime import datetime

from app.services.geocoding import GeocodingService
from app.services.kgis_fetch import KGISFetchService
from app.services.spatial_validation import SpatialValidationEngine
from app.services.risk_classifier import RiskClassifierService
from app.services.flag_mapping import FlagMappingService
from app.services.llm_explainer import LLMExplainerService

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """
    Orchestrates the full GeoSafe pipeline:
      1. Geocoding + parcel resolution
      2. Auto KGIS layer fetch
      3. Spatial validation engine
      4. Risk classifier (AI model)
      5. Legal + environmental flag mapping
      6. LLM explainability layer
      7. Safety report generation
    """

    def __init__(self):
        self.geocoding = GeocodingService()
        self.kgis_fetch = KGISFetchService()
        self.spatial_engine = SpatialValidationEngine()
        self.risk_classifier = RiskClassifierService()
        self.flag_mapper = FlagMappingService()
        self.llm_explainer = LLMExplainerService()

    async def generate_report(
        self,
        input_type: str,
        survey_input: Optional[dict] = None,
        coordinates_input: Optional[dict] = None,
        use_demo_data: bool = True,
    ) -> dict:
        """
        Full pipeline execution. Returns a dictionary matching
        the SafetyReportResponse schema.
        """
        start_time = time.time()

        # ── Step 1: Geocoding + Parcel Resolution ─────
        logger.info("Step 1: Geocoding input (type=%s)", input_type)
        try:
            geocode_result = await self.geocoding.resolve(
                input_type=input_type,
                survey_input=survey_input,
                coordinates_input=coordinates_input,
            )
        except ValueError:
            # Fallback: if survey number resolution fails, try with coordinates from village
            if input_type == "survey_number" and survey_input:
                logger.warning("Survey number resolution failed; using coordinate fallback")
                # Create a default coordinate for demo purposes
                geocode_result = await self.geocoding.resolve(
                    input_type="coordinates",
                    coordinates_input={
                        "latitude": 12.8584,
                        "longitude": 77.7842,
                        "buffer_m": 500.0,
                    },
                )
                geocode_result.source = "fallback"
                geocode_result.confidence = 0.30
                geocode_result.raw_input = (
                    f"{survey_input.get('district')}/{survey_input.get('taluk')}/"
                    f"{survey_input.get('village')}/{survey_input.get('survey_number')}"
                )
            else:
                raise

        parcel_polygon = geocode_result.polygon
        logger.info(
            "Parcel resolved: %.6f, %.6f (area=%.0f m², source=%s)",
            geocode_result.centroid_lat,
            geocode_result.centroid_lon,
            geocode_result.area_sqm,
            geocode_result.source,
        )

        # ── Step 2: Auto KGIS Layer Fetch ─────────────
        logger.info("Step 2: Fetching KGIS layers")
        if use_demo_data:
            layer_results = KGISFetchService.generate_demo_layers(parcel_polygon)
        else:
            layer_results = await self.kgis_fetch.fetch_all_layers(parcel_polygon)
        logger.info("Fetched %d layers", len(layer_results))

        # ── Step 3: Spatial Validation Engine ─────────
        logger.info("Step 3: Running spatial validation")
        validation_scores = self.spatial_engine.validate_all(parcel_polygon, layer_results)

        # ── Step 4: Risk Classifier ───────────────────
        logger.info("Step 4: Running risk classifier")
        risk_prediction = self.risk_classifier.predict(validation_scores)
        logger.info(
            "Risk: %s (confidence=%.2f, raw_score=%.4f)",
            risk_prediction.risk_level,
            risk_prediction.confidence,
            risk_prediction.raw_score,
        )

        # ── Step 5: Legal + Environmental Flag Mapping ──
        logger.info("Step 5: Mapping legal flags")
        flags = self.flag_mapper.map_flags(validation_scores)

        # ── Step 6: LLM Explainability ────────────────
        logger.info("Step 6: Generating plain-language explanation")
        parcel_info = {
            "raw_input": geocode_result.raw_input,
            "centroid_lat": geocode_result.centroid_lat,
            "centroid_lon": geocode_result.centroid_lon,
            "area_sqm": geocode_result.area_sqm,
            "source": geocode_result.source,
        }
        explanation = await self.llm_explainer.explain(
            risk=risk_prediction,
            flags=flags,
            validations=validation_scores,
            parcel_info=parcel_info,
        )

        # ── Step 7: Assemble Report ───────────────────
        processing_time_ms = int((time.time() - start_time) * 1000)
        report_id = uuid.uuid4()
        shareable_token = secrets.token_urlsafe(32)

        report = {
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat(),
            "parcel": {
                "id": uuid.uuid4(),
                "input_type": input_type,
                "raw_input": geocode_result.raw_input,
                "district": survey_input.get("district") if survey_input else None,
                "taluk": survey_input.get("taluk") if survey_input else None,
                "village": survey_input.get("village") if survey_input else None,
                "survey_number": survey_input.get("survey_number") if survey_input else None,
                "centroid_lat": geocode_result.centroid_lat,
                "centroid_lon": geocode_result.centroid_lon,
                "area_sqm": round(geocode_result.area_sqm, 2),
                "geocode_source": geocode_result.source,
                "geocode_confidence": geocode_result.confidence,
            },
            "risk_level": risk_prediction.risk_level,
            "risk_confidence": risk_prediction.confidence,
            "risk_score_raw": risk_prediction.raw_score,
            "layer_validations": [
                {
                    "layer_name": v.layer_name,
                    "layer_label": v.layer_label,
                    "intersects": v.intersects,
                    "overlap_area_sqm": v.overlap_area_sqm,
                    "overlap_pct": v.overlap_pct,
                    "buffer_distance_m": v.buffer_distance_m,
                    "nearest_feature_dist_m": v.nearest_feature_dist_m,
                    "spatial_score": v.spatial_score,
                }
                for v in validation_scores
            ],
            "legal_flags": [
                {
                    "flag_code": f.flag_code,
                    "flag_category": f.flag_category,
                    "flag_label": f.flag_label,
                    "description": f.description,
                    "severity": f.severity,
                    "act_name": f.act_name,
                    "act_section": f.act_section,
                    "clause_summary": f.clause_summary,
                    "layer_name": f.layer_name,
                    "overlap_pct": f.overlap_pct,
                }
                for f in flags
            ],
            "shap_explanations": [
                {
                    "feature_name": name,
                    "shap_value": val,
                    "direction": "increases_risk" if val > 0 else "decreases_risk",
                    "human_label": {
                        "water_bodies": "Water Body Proximity",
                        "forest_areas": "Forest Land Proximity",
                        "eco_sensitive_zones": "Eco-Sensitive Zone",
                        "flood_zones": "Flood Risk",
                        "govt_land": "Government Land",
                    }.get(name, name),
                }
                for name, val in risk_prediction.shap_values.items()
            ],
            "plain_language_summary": explanation.plain_language_summary,
            "recommended_next_steps": explanation.recommended_next_steps,
            "pdf_url": None,
            "shareable_link": f"/api/v1/reports/{shareable_token}",
            "processing_time_ms": processing_time_ms,
        }

        logger.info(
            "Report generated in %dms — risk=%s, flags=%d",
            processing_time_ms,
            risk_prediction.risk_level,
            len(flags),
        )

        return report

    async def generate_map_overlay_data(self, report: dict) -> dict:
        """
        Generate GeoJSON data for map overlay visualization.
        Returns a FeatureCollection with the parcel and all validation layers.
        """
        features = []

        # Parcel boundary
        parcel = report.get("parcel", {})
        if parcel.get("centroid_lat") and parcel.get("centroid_lon"):
            features.append({
                "type": "Feature",
                "properties": {
                    "type": "parcel",
                    "label": f"Parcel: {parcel.get('raw_input', 'Unknown')}",
                    "risk_level": report.get("risk_level", "UNKNOWN"),
                    "style": {
                        "color": {
                            "HIGH": "#ef4444",
                            "MEDIUM": "#f59e0b",
                            "LOW": "#22c55e",
                        }.get(report.get("risk_level"), "#6b7280"),
                        "weight": 3,
                        "fillOpacity": 0.2,
                    },
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [parcel["centroid_lon"], parcel["centroid_lat"]],
                },
            })

        # Layer validation markers
        for v in report.get("layer_validations", []):
            if v.get("intersects") or (v.get("spatial_score", 0) > 0.2):
                features.append({
                    "type": "Feature",
                    "properties": {
                        "type": "layer_validation",
                        "layer_name": v["layer_name"],
                        "layer_label": v.get("layer_label", v["layer_name"]),
                        "intersects": v["intersects"],
                        "overlap_pct": v["overlap_pct"],
                        "spatial_score": v["spatial_score"],
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            parcel.get("centroid_lon", 0),
                            parcel.get("centroid_lat", 0),
                        ],
                    },
                })

        return {
            "type": "FeatureCollection",
            "features": features,
        }
