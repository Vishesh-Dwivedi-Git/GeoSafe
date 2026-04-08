"""
Step 3 — Spatial Validation Engine

Uses Shapely (in-process) or PostGIS (via raw SQL) to perform:
  - ST_Intersects: does the parcel overlap with each layer?
  - ST_Area: what % of the parcel overlaps?
  - ST_Buffer: checks proximity within configured buffer distance
  - ST_Distance: nearest feature distance

Computes a spatial_score ∈ [0, 1] per layer, which feeds into the
risk classifier.
"""
import logging
from typing import Optional
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

from app.services.kgis_fetch import KGISFetchResult

logger = logging.getLogger(__name__)


class SpatialValidationScore:
    """Output of per-layer spatial validation."""
    def __init__(
        self,
        layer_name: str,
        layer_label: str,
        intersects: bool,
        overlap_area_sqm: float,
        overlap_pct: float,
        buffer_distance_m: float,
        nearest_feature_dist_m: Optional[float],
        spatial_score: float,
        raw_features: list[dict],
    ):
        self.layer_name = layer_name
        self.layer_label = layer_label
        self.intersects = intersects
        self.overlap_area_sqm = overlap_area_sqm
        self.overlap_pct = overlap_pct
        self.buffer_distance_m = buffer_distance_m
        self.nearest_feature_dist_m = nearest_feature_dist_m
        self.spatial_score = spatial_score
        self.raw_features = raw_features


class SpatialValidationEngine:
    """
    Validates a parcel polygon against each KGIS layer using
    geometric operations (all in-process via Shapely).
    """

    def __init__(self):
        # WGS-84 ↔ UTM Zone 43N for accurate area/distance in metres
        self._to_utm = Transformer.from_crs(
            "EPSG:4326", "EPSG:32643", always_xy=True
        ).transform
        self._to_wgs = Transformer.from_crs(
            "EPSG:32643", "EPSG:4326", always_xy=True
        ).transform

    def validate_all(
        self,
        parcel_polygon: Polygon,
        layer_results: list[KGISFetchResult],
    ) -> list[SpatialValidationScore]:
        """Validate parcel against every fetched layer."""
        scores: list[SpatialValidationScore] = []
        parcel_utm = transform(self._to_utm, parcel_polygon)
        parcel_area = parcel_utm.area  # m²

        for layer in layer_results:
            score = self._validate_layer(
                parcel_polygon, parcel_utm, parcel_area, layer
            )
            scores.append(score)
            logger.info(
                "Layer %-25s | intersects=%s | overlap=%.1f%% | score=%.3f",
                layer.layer_name, score.intersects, score.overlap_pct, score.spatial_score,
            )
        return scores

    def _validate_layer(
        self,
        parcel_wgs: Polygon,
        parcel_utm: Polygon,
        parcel_area_sqm: float,
        layer: KGISFetchResult,
    ) -> SpatialValidationScore:
        """Compute spatial metrics for one layer against the parcel."""
        features = layer.geojson.get("features", [])
        if not features:
            return SpatialValidationScore(
                layer_name=layer.layer_name,
                layer_label=layer.layer_label,
                intersects=False,
                overlap_area_sqm=0.0,
                overlap_pct=0.0,
                buffer_distance_m=layer.buffer_m,
                nearest_feature_dist_m=None,
                spatial_score=0.0,
                raw_features=[],
            )

        # Collect all feature geometries
        feature_geoms_wgs = []
        matching_features = []
        for feat in features:
            try:
                geom = shape(feat["geometry"])
                if geom.is_valid:
                    feature_geoms_wgs.append(geom)
                else:
                    geom = geom.buffer(0)  # fix invalid geometries
                    feature_geoms_wgs.append(geom)
            except Exception:
                continue

        if not feature_geoms_wgs:
            return SpatialValidationScore(
                layer_name=layer.layer_name,
                layer_label=layer.layer_label,
                intersects=False,
                overlap_area_sqm=0.0,
                overlap_pct=0.0,
                buffer_distance_m=layer.buffer_m,
                nearest_feature_dist_m=None,
                spatial_score=0.0,
                raw_features=[],
            )

        # Union all features
        all_features_wgs = unary_union(feature_geoms_wgs)
        all_features_utm = transform(self._to_utm, all_features_wgs)

        # ── ST_Intersects ─────────────────────────────
        intersects = parcel_utm.intersects(all_features_utm)

        # ── ST_Intersection area ──────────────────────
        overlap_area_sqm = 0.0
        overlap_pct = 0.0
        if intersects:
            intersection = parcel_utm.intersection(all_features_utm)
            overlap_area_sqm = intersection.area
            overlap_pct = (overlap_area_sqm / parcel_area_sqm * 100) if parcel_area_sqm > 0 else 0.0

        # ── Buffer proximity check ────────────────────
        buffer_hit = False
        if layer.buffer_m > 0 and not intersects:
            parcel_buffered = parcel_utm.buffer(layer.buffer_m)
            buffer_hit = parcel_buffered.intersects(all_features_utm)

        # ── ST_Distance (nearest feature) ─────────────
        nearest_dist = parcel_utm.distance(all_features_utm)  # metres

        # ── Collect intersecting feature properties ───
        for i, geom in enumerate(feature_geoms_wgs):
            geom_utm = transform(self._to_utm, geom)
            if parcel_utm.intersects(geom_utm) or parcel_utm.distance(geom_utm) < layer.buffer_m:
                matching_features.append(features[i].get("properties", {}))

        # ── Compute spatial_score ∈ [0, 1] ────────────
        spatial_score = self._compute_score(
            intersects=intersects,
            overlap_pct=overlap_pct,
            buffer_hit=buffer_hit,
            nearest_dist_m=nearest_dist,
            buffer_m=layer.buffer_m,
            layer_name=layer.layer_name,
        )

        return SpatialValidationScore(
            layer_name=layer.layer_name,
            layer_label=layer.layer_label,
            intersects=intersects,
            overlap_area_sqm=round(overlap_area_sqm, 2),
            overlap_pct=round(overlap_pct, 2),
            buffer_distance_m=layer.buffer_m,
            nearest_feature_dist_m=round(nearest_dist, 2),
            spatial_score=round(spatial_score, 4),
            raw_features=matching_features,
        )

    @staticmethod
    def _compute_score(
        intersects: bool,
        overlap_pct: float,
        buffer_hit: bool,
        nearest_dist_m: float,
        buffer_m: float,
        layer_name: str,
    ) -> float:
        """
        Heuristic scoring:
          - Direct overlap → high score (0.6 + 0.4 × overlap_pct/100)
          - Within buffer zone → medium score (0.3 – 0.5)
          - Far away → low score (0–0.1)

        Higher-weight layers (water_bodies, forest) get a multiplier.
        """
        layer_weights = {
            "water_bodies": 1.2,
            "forest_areas": 1.3,
            "eco_sensitive_zones": 1.5,
            "flood_zones": 1.0,
            "govt_land": 1.4,
            "revenue_land": 0.8,
            "water_bodies_bhuvan": 1.0,
            "forest_bhuvan": 1.0,
        }
        weight = layer_weights.get(layer_name, 1.0)

        if intersects:
            base = 0.6 + 0.4 * min(overlap_pct / 100.0, 1.0)
        elif buffer_hit:
            # Linearly scale: closer = higher score
            if buffer_m > 0 and nearest_dist_m < buffer_m:
                proximity = 1.0 - (nearest_dist_m / buffer_m)
                base = 0.3 + 0.2 * proximity
            else:
                base = 0.3
        else:
            # Far away — minimal risk
            base = max(0.0, 0.1 - (nearest_dist_m / 10000.0))

        return min(1.0, base * weight)
