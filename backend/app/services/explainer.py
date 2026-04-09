"""
Human-readable explanation generation for AI land analysis.
"""
from __future__ import annotations

from typing import Any


class ExplainerService:
    """Convert feature values into concise reasoning statements."""

    def explain(self, features: dict[str, float], risk: str) -> list[str]:
        reasons: list[tuple[float, str]] = []

        if features.get("esz_present", 0.0) >= 1.0:
            reasons.append((1.0, "Land falls inside an eco-sensitive zone."))
        if features.get("forest_present", 0.0) >= 1.0:
            reasons.append((0.95, "Land overlaps or touches protected forest land."))

        water_distance = features.get("distance_to_water", 999999.0)
        if features.get("water_present", 0.0) >= 1.0 and water_distance < 999999.0:
            reasons.append((0.8, f"Water-related feature detected within {water_distance:.0f} m of the location."))
        elif water_distance < 250:
            reasons.append((0.7, f"Land is within {water_distance:.0f} m of a water body."))

        flood_score = features.get("flood_risk", 0.0)
        if flood_score > 0.0:
            reasons.append((0.65 + flood_score * 0.2, "Bhuvan flood layer indicates flood risk at this location."))

        govt_overlap = features.get("govt_land_present", 0.0)
        if govt_overlap > 0.0:
            reasons.append(
                (
                    0.7 + govt_overlap * 0.2,
                    "Government-land thematic hit detected; title verification is recommended.",
                )
            )

        if not reasons:
            fallback = {
                "HIGH": "Multiple environmental or land-use indicators elevate this parcel to high risk.",
                "MEDIUM": "The parcel shows moderate environmental or regulatory sensitivity.",
                "LOW": "No strong environmental or regulatory conflicts were detected from the available layers.",
            }
            reasons.append((0.1, fallback.get(risk, "Risk generated from the available geospatial indicators.")))

        reasons.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in reasons[:3]]


explainer_service = ExplainerService()
