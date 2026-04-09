"""
Bhuvan WMS-first layer query service for coordinate-based land analysis.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
from typing import Any
from xml.etree import ElementTree

import httpx
from shapely.geometry import LineString, Point, Polygon

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

KARNATAKA_BOUNDS = {
    "min_lat": 11.4,
    "max_lat": 18.6,
    "min_lng": 74.0,
    "max_lng": 78.7,
}

KARNATAKA_HEURISTIC_REGIONS: list[dict[str, Any]] = [
    {
        "name": "Western Ghats Core",
        "bounds": {"min_lat": 11.8, "max_lat": 15.7, "min_lng": 74.0, "max_lng": 75.4},
        "layers": {"forest": True, "esz": True, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 70,
        "flood_score": 0.85,
        "attributes": {"forest": {"label": "Western Ghats heuristic forest belt"}},
    },
    {
        "name": "Coastal Karnataka",
        "bounds": {"min_lat": 12.7, "max_lat": 14.9, "min_lng": 74.0, "max_lng": 75.1},
        "layers": {"forest": False, "esz": False, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 120,
        "flood_score": 0.75,
    },
    {
        "name": "Malnad Interior",
        "bounds": {"min_lat": 13.0, "max_lat": 15.4, "min_lng": 75.0, "max_lng": 76.2},
        "layers": {"forest": True, "esz": False, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 140,
        "flood_score": 0.55,
    },
    {
        "name": "Kodagu-Nagarhole Belt",
        "bounds": {"min_lat": 11.9, "max_lat": 12.7, "min_lng": 75.4, "max_lng": 76.4},
        "layers": {"forest": True, "esz": True, "flood": False, "government_land": False, "water": True},
        "water_distance_m": 110,
        "flood_score": 0.25,
        "attributes": {"forest": {"label": "Kodagu/Nagarhole heuristic reserve belt"}},
    },
    {
        "name": "Bandipur-BR Hills",
        "bounds": {"min_lat": 11.7, "max_lat": 12.4, "min_lng": 76.4, "max_lng": 77.3},
        "layers": {"forest": True, "esz": True, "flood": False, "government_land": False, "water": True},
        "water_distance_m": 160,
        "flood_score": 0.2,
    },
    {
        "name": "Bhadra-Kudremukh",
        "bounds": {"min_lat": 13.0, "max_lat": 14.0, "min_lng": 75.1, "max_lng": 76.0},
        "layers": {"forest": True, "esz": True, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 90,
        "flood_score": 0.7,
    },
    {
        "name": "Dandeli-Kali",
        "bounds": {"min_lat": 14.9, "max_lat": 15.8, "min_lng": 74.2, "max_lng": 75.1},
        "layers": {"forest": True, "esz": True, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 100,
        "flood_score": 0.6,
    },
    {
        "name": "Krishna-Tungabhadra Basin",
        "bounds": {"min_lat": 15.0, "max_lat": 17.8, "min_lng": 75.0, "max_lng": 77.8},
        "layers": {"forest": False, "esz": False, "flood": True, "government_land": False, "water": True},
        "water_distance_m": 180,
        "flood_score": 0.45,
    },
    {
        "name": "Bengaluru Urban Plateau",
        "bounds": {"min_lat": 12.6, "max_lat": 13.3, "min_lng": 77.2, "max_lng": 77.9},
        "layers": {"forest": False, "esz": False, "flood": False, "government_land": False, "water": True},
        "water_distance_m": 260,
        "flood_score": 0.1,
    },
    {
        "name": "Eastern Dry Interior",
        "bounds": {"min_lat": 12.4, "max_lat": 18.4, "min_lng": 76.8, "max_lng": 78.6},
        "layers": {"forest": False, "esz": False, "flood": False, "government_land": False, "water": False},
        "water_distance_m": 420,
        "flood_score": 0.05,
    },
]


def _radius_to_bbox(lat: float, lng: float, radius_m: float) -> tuple[float, float, float, float]:
    lat_delta = radius_m / 111320.0
    lon_delta = radius_m / max(111320.0 * math.cos(math.radians(lat)), 1e-6)
    return (lng - lon_delta, lat - lat_delta, lng + lon_delta, lat + lat_delta)


class LayerService:
    """Query Bhuvan WMS layers by coordinate and optional OSM water proximity."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = settings.GIS_LAYER_CACHE_TTL_SECONDS
        self._overpass_endpoints = [
            settings.OVERPASS_API_URL,
            "https://overpass.kumi.systems/api/interpreter",
        ]
        self._fallback_points: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        logger.info("Layer cache initialized with TTL=%ss", self._ttl)
        self._load_fallback_points()

    async def get_layers(self, lat: float, lng: float, radius_m: float) -> dict[str, Any]:
        forest = await self.get_bhuvan_layer_info(
            lat,
            lng,
            "forest",
            settings.BHUVAN_FOREST_WMS_URL,
            settings.BHUVAN_FOREST_LAYER_NAME,
        )
        esz = await self.get_bhuvan_layer_info(
            lat,
            lng,
            "esz",
            settings.BHUVAN_ESZ_WMS_URL,
            settings.BHUVAN_ESZ_LAYER_NAME,
        )
        flood = await self.get_bhuvan_layer_info(
            lat,
            lng,
            "flood",
            settings.BHUVAN_FLOOD_WMS_URL,
            settings.BHUVAN_FLOOD_LAYER_NAME,
        )
        govt_land = await self.get_bhuvan_layer_info(
            lat,
            lng,
            "government_land",
            settings.BHUVAN_GOVT_LAND_WMS_URL,
            settings.BHUVAN_GOVT_LAND_LAYER_NAME,
        )
        water = await self.get_water_bodies(lat, lng, radius_m)

        layers = {
            "water": water,
            "forest": forest,
            "esz": esz,
            "flood": flood,
            "government_land": govt_land,
        }
        layers = self._apply_fallback_points(lat, lng, layers)
        layers = self._apply_karnataka_heuristics(lat, lng, layers)
        logger.info(
            "Bhuvan/OSM layer hits: %s",
            {name: value.get("present") if isinstance(value, dict) else None for name, value in layers.items()},
        )
        return layers

    async def get_bhuvan_layer_info(
        self,
        lat: float,
        lng: float,
        layer_name: str,
        wms_url: str | None,
        layer_id: str | None,
    ) -> dict[str, Any]:
        if not wms_url or not layer_id:
            logger.warning("Bhuvan WMS not configured for layer '%s'", layer_name)
            return {"present": False, "attributes": {}, "source": "unconfigured"}

        cache_key = f"bhuvan:{layer_name}:{lat:.6f}:{lng:.6f}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        bbox = _radius_to_bbox(lat, lng, 250.0)
        params = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetFeatureInfo",
            "LAYERS": layer_id,
            "QUERY_LAYERS": layer_id,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "WIDTH": 101,
            "HEIGHT": 101,
            "X": 50,
            "Y": 50,
            "INFO_FORMAT": "application/json",
            "FEATURE_COUNT": 5,
        }
        fallback_params = dict(params)
        fallback_params["INFO_FORMAT"] = "text/plain"

        for request_params in (params, fallback_params):
            try:
                response = await self._client.get(wms_url, params=request_params)
                response.raise_for_status()
                parsed = self._parse_getfeatureinfo_response(response)
                result = {
                    "present": parsed["present"],
                    "attributes": parsed["attributes"],
                    "source": "bhuvan_wms",
                    "wms_url": wms_url,
                    "layer_name": layer_id,
                }
                self._set_cache(cache_key, result)
                return result
            except Exception as exc:
                logger.warning("Bhuvan GetFeatureInfo failed for layer '%s': %s", layer_name, exc)

        return {"present": False, "attributes": {}, "source": "bhuvan_wms_failed"}

    async def get_water_bodies(self, lat: float, lng: float, radius_m: float) -> dict[str, Any]:
        bbox = _radius_to_bbox(lat, lng, radius_m)
        cache_key = f"water:{lat:.6f}:{lng:.6f}:{radius_m:.0f}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        query = f"""
        [out:json][timeout:25];
        (
          way["natural"="water"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          relation["natural"="water"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          way["waterway"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          relation["waterway"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          way["landuse"="reservoir"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
        );
        out geom;
        """

        try:
            payload = await self._post_overpass(query)
            water_geometries = []
            for element in payload.get("elements", []):
                geometry = element.get("geometry") or []
                if len(geometry) < 2:
                    continue
                coords = [(point["lon"], point["lat"]) for point in geometry]
                geom = None
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    try:
                        geom = Polygon(coords)
                    except Exception:
                        geom = None
                if geom is None:
                    try:
                        geom = LineString(coords)
                    except Exception:
                        continue
                water_geometries.append(geom)

            distance_m = self._distance_to_geometries(lat, lng, water_geometries)
            result = {
                "present": bool(water_geometries),
                "distance_m": distance_m,
                "count": len(water_geometries),
                "source": "osm_overpass",
            }
            self._set_cache(cache_key, result)
            return result
        except Exception as exc:
            logger.warning("OSM water fetch failed: %s", exc)
            return {"present": False, "distance_m": 999999.0, "count": 0, "source": "osm_failed"}

    def _parse_getfeatureinfo_response(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "").lower()
        text = response.text.strip()
        lowered = text.lower()

        if (
            not text
            or "no features were found" in lowered
            or "no features" in lowered
            or "serviceexception" in lowered
            or "not queryable" in lowered
        ):
            return {"present": False, "attributes": {}}

        if "json" in content_type:
            data = response.json()
            features = data.get("features") or data.get("results") or []
            if isinstance(features, list) and features:
                props = (features[0].get("properties") or {}) if isinstance(features[0], dict) else {}
                return {"present": True, "attributes": props}
            if data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list):
                return {"present": False, "attributes": {}}
            if isinstance(data, dict) and any(
                key.lower() in {"error", "errors", "exception", "serviceexception"}
                for key in data.keys()
            ):
                return {"present": False, "attributes": {}}
            if isinstance(data, dict) and data and not any(
                isinstance(value, str) and "no features" in value.lower() for value in data.values()
            ):
                return {"present": True, "attributes": data}
            return {"present": False, "attributes": {}}

        if text.startswith("<"):
            try:
                root = ElementTree.fromstring(text)
                if root.tag.lower().endswith("serviceexceptionreport"):
                    return {"present": False, "attributes": {}}
                attributes = {child.tag.split("}")[-1]: (child.text or "") for child in root.iter() if child is not root}
                return {"present": bool(attributes), "attributes": attributes}
            except Exception:
                pass

        try:
            data = json.loads(text)
            if isinstance(data, dict) and data:
                return {"present": True, "attributes": data}
        except Exception:
            pass

        return {"present": True, "attributes": {"raw": text[:500]}}

    async def _post_overpass(self, query: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for index, endpoint in enumerate(self._overpass_endpoints):
            try:
                response = await self._client.post(endpoint, data={"data": query})
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(1.0 + index)
        raise RuntimeError(f"All Overpass endpoints failed: {last_error}")

    def _distance_to_geometries(self, lat: float, lng: float, geometries: list[Any]) -> float:
        if not geometries:
            return 999999.0
        point = Point(lng, lat)
        distances = [self._planar_distance_m(point, geometry) for geometry in geometries]
        return round(min(distances), 2)

    @staticmethod
    def _planar_distance_m(point: Point, geometry: Any) -> float:
        degrees = point.distance(geometry)
        return degrees * 111320.0

    def _get_cache(self, key: str) -> Any | None:
        cached = self._cache.get(key)
        if cached and time.time() - cached[0] < self._ttl:
            return cached[1]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def _load_fallback_points(self) -> None:
        path = settings.FALLBACK_POINTS_PATH
        if not path:
            self._fallback_points = []
            return

        resolved = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        if not os.path.exists(resolved):
            logger.info("Fallback points file not found at %s; continuing without hardcoded points", resolved)
            self._fallback_points = []
            return

        try:
            with open(resolved, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self._fallback_points = payload if isinstance(payload, list) else []
            logger.info("Loaded %d fallback points from %s", len(self._fallback_points), resolved)
        except Exception as exc:
            logger.warning("Failed to load fallback points from %s: %s", resolved, exc)
            self._fallback_points = []

    def _apply_fallback_points(self, lat: float, lng: float, layers: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        fallback = self._nearest_fallback_point(lat, lng)
        if fallback is None:
            return layers

        logger.info("Applying nearest fallback point '%s' for lat=%.6f lng=%.6f", fallback.get("name", "unnamed"), lat, lng)
        merged = {key: dict(value) for key, value in layers.items()}
        fallback_layers = fallback.get("layers") or {}
        fallback_attrs = fallback.get("attributes") or {}

        for layer_name in ("forest", "esz", "flood", "government_land"):
            if not merged.get(layer_name, {}).get("present") and bool(fallback_layers.get(layer_name)):
                merged[layer_name] = {
                    "present": True,
                    "attributes": fallback_attrs.get(layer_name, {}),
                    "source": "coordinate_fallback",
                }

        if not merged.get("water", {}).get("present") and bool(fallback_layers.get("water")):
            merged["water"] = {
                "present": True,
                "distance_m": float(fallback.get("water_distance_m", 999999.0)),
                "count": 1,
                "source": "coordinate_fallback",
            }
        return merged

    def _apply_karnataka_heuristics(self, lat: float, lng: float, layers: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if not settings.ENABLE_KARNATAKA_HEURISTIC_FALLBACK or not self._is_inside_karnataka(lat, lng):
            return layers

        matches = [region for region in KARNATAKA_HEURISTIC_REGIONS if self._region_matches(lat, lng, region)]
        if not matches:
            return layers

        merged = {key: dict(value) for key, value in layers.items()}
        names = ", ".join(region["name"] for region in matches)
        logger.info("Applying Karnataka heuristic fallback for lat=%.6f lng=%.6f using regions: %s", lat, lng, names)

        for region in matches:
            region_layers = region.get("layers") or {}
            region_attrs = region.get("attributes") or {}

            for layer_name in ("forest", "esz", "government_land"):
                if merged.get(layer_name, {}).get("present"):
                    continue
                if bool(region_layers.get(layer_name)):
                    merged[layer_name] = {
                        "present": True,
                        "attributes": {
                            "source": "karnataka_heuristic",
                            "region": region["name"],
                            **region_attrs.get(layer_name, {}),
                        },
                        "source": "karnataka_heuristic",
                    }

            if not merged.get("flood", {}).get("present") and bool(region_layers.get("flood")):
                merged["flood"] = {
                    "present": True,
                    "attributes": {"source": "karnataka_heuristic", "region": region["name"]},
                    "score": float(region.get("flood_score", 0.5)),
                    "source": "karnataka_heuristic",
                }

            current_water = merged.get("water", {})
            heuristic_water_present = bool(region_layers.get("water"))
            heuristic_water_distance = float(region.get("water_distance_m", 999999.0))
            if not current_water.get("present") and heuristic_water_present:
                merged["water"] = {
                    "present": True,
                    "distance_m": heuristic_water_distance,
                    "count": 1,
                    "source": "karnataka_heuristic",
                }
            elif current_water.get("present") and current_water.get("distance_m", 999999.0) > heuristic_water_distance:
                merged["water"]["distance_m"] = heuristic_water_distance

        return merged

    def _nearest_fallback_point(self, lat: float, lng: float) -> dict[str, Any] | None:
        best: tuple[float, dict[str, Any]] | None = None
        for point in self._fallback_points:
            plat = point.get("latitude")
            plng = point.get("longitude")
            if plat is None or plng is None:
                continue
            distance = self._distance_between_points_m(lat, lng, float(plat), float(plng))
            radius = float(point.get("radius_m", settings.FALLBACK_POINT_RADIUS_M))
            if distance > radius:
                continue
            if best is None or distance < best[0]:
                best = (distance, point)
        return best[1] if best is not None else None

    @staticmethod
    def _is_inside_karnataka(lat: float, lng: float) -> bool:
        return (
            KARNATAKA_BOUNDS["min_lat"] <= lat <= KARNATAKA_BOUNDS["max_lat"]
            and KARNATAKA_BOUNDS["min_lng"] <= lng <= KARNATAKA_BOUNDS["max_lng"]
        )

    @staticmethod
    def _region_matches(lat: float, lng: float, region: dict[str, Any]) -> bool:
        bounds = region.get("bounds") or {}
        return (
            float(bounds.get("min_lat", -90)) <= lat <= float(bounds.get("max_lat", 90))
            and float(bounds.get("min_lng", -180)) <= lng <= float(bounds.get("max_lng", 180))
        )

    @staticmethod
    def _distance_between_points_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        dlat = (lat2 - lat1) * 111320.0
        dlng = (lng2 - lng1) * 111320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
        return math.sqrt(dlat * dlat + dlng * dlng)
