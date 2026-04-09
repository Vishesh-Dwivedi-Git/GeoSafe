"""
Step 2 - Compliance layer fetch.

Mixed approach:
  - KGIS Web APIs remain the source of truth for parcel/admin resolution.
  - Compliance layers are fetched from polygon-capable GeoJSON sources when available.
  - KGIS Nearby Assets remains an optional fallback for approximation-only use cases.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from pyproj import Transformer
from shapely.geometry import Point, Polygon, box, mapping, shape
from shapely.ops import transform

from app.config import get_settings
from app.services.kgis_webapi import KGISWebAPIService

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_layer_catalog() -> dict[str, dict[str, Any]]:
    return {
        "water_bodies": {
            "label": "Water Bodies & Lake Boundaries",
            "buffer_m": 200,
            "geojson_path": settings.KGIS_LAYER_WATER_BODIES_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_WATER_BODIES_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_WATER_BODIES,
        },
        "forest_areas": {
            "label": "Forest & Eco-Sensitive Zones",
            "buffer_m": 500,
            "geojson_path": settings.KGIS_LAYER_FOREST_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_FOREST_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_FOREST,
        },
        "eco_sensitive_zones": {
            "label": "Eco-Sensitive Zones (ESZ)",
            "buffer_m": 300,
            "geojson_path": settings.KGIS_LAYER_ECO_SENSITIVE_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_ECO_SENSITIVE_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_ECO_SENSITIVE,
        },
        "flood_zones": {
            "label": "Flood-Prone Zones",
            "buffer_m": 100,
            "geojson_path": settings.KGIS_LAYER_FLOOD_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_FLOOD_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_FLOOD,
        },
        "govt_land": {
            "label": "Government-Acquired Land",
            "buffer_m": 0,
            "geojson_path": settings.KGIS_LAYER_GOVT_LAND_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_GOVT_LAND_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_GOVT_LAND,
        },
        "revenue_land": {
            "label": "Revenue Land Records",
            "buffer_m": 0,
            "geojson_path": settings.KGIS_LAYER_REVENUE_LAND_GEOJSON_PATH,
            "geojson_url": settings.KGIS_LAYER_REVENUE_LAND_GEOJSON_URL,
            "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_REVENUE_LAND,
        },
    }


KGIS_LAYERS = _build_layer_catalog()
BHUVAN_LAYERS: dict[str, dict[str, Any]] = {}


class KGISFetchResult:
    """Container for one fetched layer's GeoJSON."""

    def __init__(
        self,
        layer_name: str,
        layer_label: str,
        source: str,
        buffer_m: float,
        geojson: dict[str, Any],
        feature_count: int,
        bbox_wkt: str,
    ):
        self.layer_name = layer_name
        self.layer_label = layer_label
        self.source = source
        self.buffer_m = buffer_m
        self.geojson = geojson
        self.feature_count = feature_count
        self.bbox_wkt = bbox_wkt


class KGISFetchService:
    """Fetch compliance layers using polygon sources first, asset proximity as fallback."""

    def __init__(self):
        self._kgis_webapi = KGISWebAPIService()
        self._http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True).transform
        self.layers = _build_layer_catalog()

    async def fetch_all_layers(
        self,
        parcel_polygon: Polygon,
        buffer_km: float = 2.0,
    ) -> list[KGISFetchResult]:
        bounds = parcel_polygon.bounds
        deg_buffer = buffer_km / 111.0
        bbox = (
            bounds[0] - deg_buffer,
            bounds[1] - deg_buffer,
            bounds[2] + deg_buffer,
            bounds[3] + deg_buffer,
        )
        bbox_polygon = box(*bbox)
        bbox_wkt = bbox_polygon.wkt

        centroid = parcel_polygon.centroid
        lat = centroid.y
        lon = centroid.x

        results: list[KGISFetchResult] = []
        for name, layer_cfg in self.layers.items():
            geojson, source = await self._fetch_layer(
                layer_name=name,
                layer_cfg=layer_cfg,
                bbox_polygon=bbox_polygon,
                latitude=lat,
                longitude=lon,
            )

            results.append(
                KGISFetchResult(
                    layer_name=name,
                    layer_label=layer_cfg["label"],
                    source=source,
                    buffer_m=layer_cfg["buffer_m"],
                    geojson=geojson,
                    feature_count=len(geojson.get("features", [])),
                    bbox_wkt=bbox_wkt,
                )
            )

        logger.info(
            "Fetched %d compliance layers - total features: %d",
            len(results),
            sum(r.feature_count for r in results),
        )
        return results

    async def _fetch_layer(
        self,
        layer_name: str,
        layer_cfg: dict[str, Any],
        bbox_polygon: Polygon,
        latitude: float,
        longitude: float,
    ) -> tuple[dict[str, Any], str]:
        file_path = layer_cfg.get("geojson_path")
        if file_path:
            geojson = self._load_geojson_file(str(file_path), bbox_polygon)
            if geojson.get("features"):
                return geojson, "geojson_file"

        geojson_url = layer_cfg.get("geojson_url")
        if geojson_url:
            geojson = await self._load_geojson_url(str(geojson_url), bbox_polygon)
            if geojson.get("features"):
                return geojson, "geojson_url"

        layer_code = layer_cfg.get("nearby_asset_code")
        if layer_code:
            geojson = await self._fetch_nearby_assets_layer(
                layer_code=str(layer_code),
                latitude=latitude,
                longitude=longitude,
                buffer_m=float(layer_cfg["buffer_m"]),
            )
            if geojson.get("features"):
                return geojson, "nearby_assets"

        logger.info(
            "No configured polygon source for layer=%s; returning empty feature collection",
            layer_name,
        )
        return {"type": "FeatureCollection", "features": []}, "unconfigured"

    def _load_geojson_file(self, path: str, bbox_polygon: Polygon) -> dict[str, Any]:
        try:
            resolved = os.path.abspath(path)
            with open(resolved, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return self._clip_geojson(payload, bbox_polygon, source=f"file:{resolved}")
        except Exception as exc:
            logger.warning("GeoJSON file fetch failed for %s: %s", path, exc)
            return {"type": "FeatureCollection", "features": []}

    async def _load_geojson_url(self, url: str, bbox_polygon: Polygon) -> dict[str, Any]:
        try:
            bbox = ",".join(f"{value:.6f}" for value in bbox_polygon.bounds)
            resolved_url = url.replace("{bbox}", bbox)
            response = await self._http.get(resolved_url)
            response.raise_for_status()
            payload = response.json()
            return self._clip_geojson(payload, bbox_polygon, source=f"url:{resolved_url}")
        except Exception as exc:
            logger.warning("GeoJSON URL fetch failed for %s: %s", url, exc)
            return {"type": "FeatureCollection", "features": []}

    def _clip_geojson(
        self,
        payload: dict[str, Any],
        bbox_polygon: Polygon,
        source: str,
    ) -> dict[str, Any]:
        features = payload.get("features", []) if isinstance(payload, dict) else []
        clipped_features: list[dict[str, Any]] = []

        for feature in features:
            if not isinstance(feature, dict):
                continue
            geometry = feature.get("geometry")
            if not geometry:
                continue

            try:
                geom = shape(geometry)
            except Exception:
                continue

            if geom.is_empty:
                continue
            if not geom.is_valid:
                geom = geom.buffer(0)
            if geom.is_empty or not geom.intersects(bbox_polygon):
                continue

            properties = dict(feature.get("properties") or {})
            properties.setdefault("source", source)

            clipped_features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": mapping(geom),
                }
            )

        return {"type": "FeatureCollection", "features": clipped_features}

    async def _fetch_nearby_assets_layer(
        self,
        layer_code: str,
        latitude: float,
        longitude: float,
        buffer_m: float,
    ) -> dict[str, Any]:
        """
        Nearby Assets remains an approximation fallback. It yields point-like assets,
        which we expand into tiny polygons so the existing spatial engine can still run.
        """
        try:
            data = await self._kgis_webapi.nearby_assets(
                layer_code=layer_code,
                latitude=latitude,
                longitude=longitude,
                number=25,
                coord_type="DD",
            )
            rows = data.get("items", []) if isinstance(data, dict) else []
            features = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("msg", "")).lower().startswith("layer name not found"):
                    continue
                x = row.get("x")
                y = row.get("y")
                if x is None or y is None:
                    continue
                try:
                    x_val = float(x)
                    y_val = float(y)
                except Exception:
                    continue

                if abs(x_val) <= 180 and abs(y_val) <= 90:
                    lon, lat = x_val, y_val
                else:
                    point = transform(self._to_wgs, Point(x_val, y_val))
                    lon, lat = point.x, point.y

                deg = max(0.00015, (buffer_m or 120.0) / 111000.0)
                poly = Point(lon, lat).buffer(deg, resolution=16)
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "name": row.get("assetName", ""),
                            "distance_m": row.get("distance"),
                            "address": row.get("address", ""),
                            "asset_type": row.get("asseType", ""),
                            "source": "nearby_assets",
                            "layer_code": layer_code,
                        },
                        "geometry": mapping(poly),
                    }
                )
            return {"type": "FeatureCollection", "features": features}
        except Exception as exc:
            logger.warning("NearbyAssets fetch failed for layer_code=%s: %s", layer_code, exc)
            return {"type": "FeatureCollection", "features": []}

    @staticmethod
    def generate_demo_layers(parcel_polygon: Polygon) -> list[KGISFetchResult]:
        """
        Development fallback mode: keep the layer shell even when no datasets are wired yet.
        """
        bounds = parcel_polygon.bounds
        bbox_wkt = box(*bounds).wkt
        return [
            KGISFetchResult(
                layer_name=name,
                layer_label=cfg["label"],
                source="demo",
                buffer_m=cfg["buffer_m"],
                geojson={"type": "FeatureCollection", "features": []},
                feature_count=0,
                bbox_wkt=bbox_wkt,
            )
            for name, cfg in _build_layer_catalog().items()
        ]
