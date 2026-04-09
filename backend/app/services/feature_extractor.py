"""
Point-based feature extraction for Bhuvan WMS-driven land analysis.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Turn Bhuvan/OSM point-query hits into an ML-ready feature vector."""

    def extract(self, query_point: dict[str, float], layers: dict[str, Any]) -> dict[str, float]:
        water = layers.get("water") or {}
        forest = layers.get("forest") or {}
        esz = layers.get("esz") or {}
        flood = layers.get("flood") or {}
        govt = layers.get("government_land") or {}

        if not water.get("present"):
            logger.warning("No water feature found for coordinate query; using safe defaults")
        if not forest.get("present"):
            logger.warning("No forest feature found for coordinate query")
        if not esz.get("present"):
            logger.warning("No ESZ feature found for coordinate query")
        if not flood.get("present"):
            logger.warning("No flood feature found for coordinate query")
        if not govt.get("present"):
            logger.warning("No government land feature found for coordinate query")

        distance_to_water = float(water.get("distance_m", 999999.0))
        water_present = 1.0 if water.get("present") else 0.0
        forest_present = 1.0 if forest.get("present") else 0.0
        esz_present = 1.0 if esz.get("present") else 0.0
        flood_risk = float(flood.get("score", 1.0 if flood.get("present") else 0.0))
        govt_land_present = 1.0 if govt.get("present") else 0.0

        features = {
            "distance_to_water": round(distance_to_water, 2),
            "water_present": water_present,
            "forest_present": forest_present,
            "esz_present": esz_present,
            "flood_risk": flood_risk,
            "govt_land_present": govt_land_present,
        }
        logger.info(
            "Generated point-based feature vector at lat=%s lng=%s: %s",
            query_point.get("lat"),
            query_point.get("lng"),
            features,
        )
        return features
