"""
Step 1 - Geocoding and Parcel Resolution.

Converts user input (survey number or lat/lon) into a boundary polygon.

Sources (priority):
1) KGIS Web API (survey polygon lookup)
2) Bhunaksha / Dharitri (survey lookup fallbacks)
3) Nominatim / OpenStreetMap (village centroid fallback)
4) Manual coordinate buffer
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx
from pyproj import Transformer
from shapely import wkt
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union

from app.config import get_settings
from app.services.kgis_webapi import KGISWebAPIService

logger = logging.getLogger(__name__)
settings = get_settings()


class GeocodingResult:
    """Container for geocoding output."""

    def __init__(
        self,
        polygon: Polygon,
        centroid_lat: float,
        centroid_lon: float,
        area_sqm: float,
        source: str,
        confidence: float,
        raw_input: str,
    ):
        self.polygon = polygon
        self.centroid_lat = centroid_lat
        self.centroid_lon = centroid_lon
        self.area_sqm = area_sqm
        self.source = source
        self.confidence = confidence
        self.raw_input = raw_input

    def to_geojson(self) -> dict:
        return mapping(self.polygon)

    def to_wkt(self) -> str:
        return self.polygon.wkt


class GeocodingService:
    """Resolve user input to parcel boundary polygon."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._kgis_webapi = KGISWebAPIService()
        # WGS-84 -> UTM Zone 43N (good default for Karnataka)
        self._to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform
        self._to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True).transform

    async def resolve(
        self,
        input_type: str,
        survey_input: Optional[dict] = None,
        coordinates_input: Optional[dict] = None,
    ) -> GeocodingResult:
        """Main entry point for both survey-number and coordinate input."""
        if input_type == "survey_number" and survey_input:
            return await self._resolve_survey_number(survey_input)
        if input_type == "coordinates" and coordinates_input:
            return self._resolve_coordinates(coordinates_input)
        raise ValueError(f"Invalid input_type: {input_type}")

    async def _resolve_survey_number(self, inp: dict) -> GeocodingResult:
        """Attempt KGIS first, then cadastral fallbacks, then Nominatim fallback."""
        raw = f"{inp.get('district')}/{inp.get('taluk')}/{inp.get('village')}/{inp.get('survey_number')}"

        result = await self._try_kgis_webapi_survey(inp)
        if result:
            logger.info("Resolved via KGIS webapi: %s", raw)
            return result

        result = await self._try_bhunaksha(inp)
        if result:
            logger.info("Resolved via Bhunaksha: %s", raw)
            return result

        result = await self._try_dharitri(inp)
        if result:
            logger.info("Resolved via Dharitri: %s", raw)
            return result

        result = await self._try_nominatim_survey(inp)
        if result:
            logger.info("Resolved via Nominatim fallback: %s", raw)
            return result

        raise ValueError(
            f"Could not resolve survey number: {raw}. "
            "Please verify district/taluk/village/survey details or try coordinates."
        )

    async def _try_kgis_webapi_survey(self, inp: dict) -> Optional[GeocodingResult]:
        """
        KGIS sequence (doc-aligned):
          1) getlocationdetails (derive villageCode when needed)
          2) surveyno (validate survey exists in village)
          3) geomForSurveyNum (fetch polygon geometry)
        """
        survey_number = str(inp.get("survey_number") or "").strip()
        if not survey_number:
            return None

        village_code = (inp.get("village_code") or "").strip() or None
        lat: Optional[float] = None
        lon: Optional[float] = None

        # Optional direct coordinates in input (if caller includes them)
        try:
            if inp.get("latitude") is not None and inp.get("longitude") is not None:
                lat = float(inp["latitude"])
                lon = float(inp["longitude"])
        except Exception:
            lat = None
            lon = None

        # If village code missing, try infer from village centroid via Nominatim + KGIS location details
        if not village_code:
            lat, lon = await self._infer_village_coordinates(inp)
            if lat is not None and lon is not None:
                village_code = await self._infer_village_code_from_coords(lat, lon)

        if not village_code:
            logger.info("KGIS webapi skipped: village_code unavailable for survey lookup")
            return None

        try:
            # Step-2: surveyno validation (if coordinates available)
            survey_exists = True
            if lat is not None and lon is not None:
                survey_list_payload = await self._kgis_webapi.survey_numbers(
                    village_code=village_code,
                    latitude=lat,
                    longitude=lon,
                    distance_m=5000,
                )
                survey_values = self._extract_survey_numbers(survey_list_payload)
                if survey_values:
                    normalized_target = self._normalize_survey_token(survey_number)
                    survey_exists = any(
                        self._normalize_survey_token(item) == normalized_target
                        for item in survey_values
                    )
                else:
                    # If list endpoint gives no survey list, continue geometry attempt.
                    survey_exists = True

            if not survey_exists:
                logger.info(
                    "KGIS surveyno validation failed for village_code=%s survey=%s",
                    village_code,
                    survey_number,
                )
                return None

            # Step-3: geometry fetch via geomForSurveyNum path
            for survey_candidate in self._survey_variants(survey_number):
                data = await self._kgis_webapi.geometric_polygon_area(village_code, survey_candidate)
                poly = self._extract_polygon_from_geom_payload(data)
                if not poly or poly.is_empty:
                    continue

                centroid = poly.centroid
                area = self._compute_area(poly)
                raw = f"{inp.get('district')}/{inp.get('taluk')}/{inp.get('village')}/{survey_candidate}"
                return GeocodingResult(
                    polygon=poly,
                    centroid_lat=centroid.y,
                    centroid_lon=centroid.x,
                    area_sqm=area,
                    source="kgis_webapi",
                    confidence=0.98,
                    raw_input=raw,
                )

            if lat is not None and lon is not None:
                near = await self._kgis_webapi.survey_numbers(village_code, lat, lon, distance_m=5000)
                logger.info("KGIS surveyno lookup for village_code=%s returned: %s", village_code, near)
        except Exception as exc:
            logger.warning("KGIS webapi survey lookup failed: %s", exc)
            return None
        return None

    async def _try_bhunaksha(self, inp: dict) -> Optional[GeocodingResult]:
        """Query Bhunaksha cadastral API for parcel geometry."""
        try:
            url = f"{settings.BHUNAKSHA_BASE_URL}/Api/parcel"
            params = {
                "state": "karnataka",
                "district": inp.get("district", ""),
                "taluk": inp.get("taluk", ""),
                "village": inp.get("village", ""),
                "surveyNo": inp.get("survey_number", ""),
            }
            resp = await self._client.get(url, params=params)
            if resp.status_code != 200:
                return None

            data = resp.json()
            if not data.get("geometry"):
                return None

            poly = self._geometry_to_polygon(data["geometry"])
            if not poly:
                return None

            centroid = poly.centroid
            area = self._compute_area(poly)
            raw = f"{inp.get('district')}/{inp.get('taluk')}/{inp.get('village')}/{inp.get('survey_number')}"
            return GeocodingResult(
                polygon=poly,
                centroid_lat=centroid.y,
                centroid_lon=centroid.x,
                area_sqm=area,
                source="bhunaksha",
                confidence=0.95,
                raw_input=raw,
            )
        except Exception as exc:
            logger.warning("Bhunaksha lookup failed: %s", exc)
            return None

    async def _try_dharitri(self, inp: dict) -> Optional[GeocodingResult]:
        """Query Karnataka Dharitri API for parcel geometry."""
        try:
            url = f"{settings.DHARITRI_BASE_URL}/api/parcel/geometry"
            payload = {
                "district": inp.get("district", ""),
                "taluk": inp.get("taluk", ""),
                "hobli": inp.get("hobli", ""),
                "village": inp.get("village", ""),
                "surveyNumber": inp.get("survey_number", ""),
            }
            resp = await self._client.post(url, json=payload)
            if resp.status_code != 200:
                return None

            data = resp.json()
            features = data.get("features") or []
            if not features:
                return None

            poly = self._geometry_to_polygon(features[0].get("geometry"))
            if not poly:
                return None

            centroid = poly.centroid
            area = self._compute_area(poly)
            raw = f"{inp.get('district')}/{inp.get('taluk')}/{inp.get('village')}/{inp.get('survey_number')}"
            return GeocodingResult(
                polygon=poly,
                centroid_lat=centroid.y,
                centroid_lon=centroid.x,
                area_sqm=area,
                source="dharitri",
                confidence=0.90,
                raw_input=raw,
            )
        except Exception as exc:
            logger.warning("Dharitri lookup failed: %s", exc)
            return None

    async def _try_nominatim_survey(self, inp: dict) -> Optional[GeocodingResult]:
        """Geocode village name via Nominatim and create 500m fallback buffer."""
        try:
            query = f"{inp.get('village')}, {inp.get('taluk')}, {inp.get('district')}, Karnataka, India"
            url = f"{settings.NOMINATIM_URL}/search"
            params = {"q": query, "format": "json", "limit": 1}
            headers = {"User-Agent": "GeoSafe/1.0"}
            resp = await self._client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None

            results = resp.json()
            if not results:
                return None

            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            poly = self._create_buffer_polygon(lat, lon, radius_m=500)
            area = self._compute_area(poly)
            raw = f"{inp.get('district')}/{inp.get('taluk')}/{inp.get('village')}/{inp.get('survey_number')}"
            return GeocodingResult(
                polygon=poly,
                centroid_lat=lat,
                centroid_lon=lon,
                area_sqm=area,
                source="nominatim",
                confidence=0.50,
                raw_input=raw,
            )
        except Exception as exc:
            logger.warning("Nominatim lookup failed: %s", exc)
            return None

    async def _infer_village_coordinates(self, inp: dict) -> tuple[Optional[float], Optional[float]]:
        """Infer village centroid using Nominatim for downstream KGIS village_code lookup."""
        try:
            query = f"{inp.get('village')}, {inp.get('taluk')}, {inp.get('district')}, Karnataka, India"
            url = f"{settings.NOMINATIM_URL}/search"
            params = {"q": query, "format": "json", "limit": 1}
            headers = {"User-Agent": "GeoSafe/1.0"}
            resp = await self._client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return (None, None)
            results = resp.json() or []
            if not results:
                return (None, None)
            return (float(results[0]["lat"]), float(results[0]["lon"]))
        except Exception:
            return (None, None)

    async def _infer_village_code_from_coords(self, lat: float, lon: float) -> Optional[str]:
        """Infer KGIS village code from coordinate-based location details response."""
        try:
            data = await self._kgis_webapi.location_details(lat, lon, aoi="w")
            code = self._find_key_recursive(
                data,
                (
                    "villageCode",
                    "villagecode",
                    "vcode",
                    "village_code",
                    "villageLgdCode",
                    "lgdVillageCode",
                ),
            )
            if code:
                return str(code).strip()
        except Exception as exc:
            logger.warning("KGIS getlocationdetails lookup failed: %s", exc)

        try:
            near = await self._kgis_webapi.nearby_admin_hierarchy(lat, lon, distance_m=5000, aoi="d,t,h,v")
            code = self._find_key_recursive(
                near,
                (
                    "villageCode",
                    "villagecode",
                    "vcode",
                    "village_code",
                    "villageLgdCode",
                    "lgdVillageCode",
                ),
            )
            if code:
                return str(code).strip()
        except Exception as exc:
            logger.warning("KGIS nearby_admin_hierarchy village-code lookup failed: %s", exc)
        return None

    @staticmethod
    def _survey_variants(survey_number: str) -> list[str]:
        """Try likely KGIS survey number formats."""
        raw = survey_number.strip()
        variants = [
            raw,
            raw.replace(" ", ""),
            raw.replace("-", "/"),
            raw.replace("/", "-"),
            raw.split("/")[0] if "/" in raw else raw,
        ]
        out: list[str] = []
        for value in variants:
            if value and value not in out:
                out.append(value)
        return out

    @staticmethod
    def _normalize_survey_token(value: str) -> str:
        return "".join((value or "").strip().lower().replace("-", "/").split())

    def _extract_survey_numbers(self, payload: Any) -> list[str]:
        """Extract sno[] values from surveyno response."""
        out: list[str] = []
        if isinstance(payload, dict):
            entries = payload.get("surveynumber")
            if isinstance(entries, list):
                for item in entries:
                    if isinstance(item, dict):
                        sno = item.get("sno")
                        if sno is not None:
                            out.append(str(sno))
            if "items" in payload and isinstance(payload["items"], list):
                for item in payload["items"]:
                    if isinstance(item, dict) and item.get("sno") is not None:
                        out.append(str(item["sno"]))
        return out

    def _extract_polygon_from_geom_payload(self, payload: Any) -> Optional[Polygon]:
        """
        Parse geomForSurveyNum payload:
          [{"message":"200","geom":"POLYGON (...)"}]
        Can include multiple polygons for same survey.
        """
        wkts: list[str] = []
        rows: list[Any] = []

        if isinstance(payload, dict):
            if isinstance(payload.get("items"), list):
                rows = payload["items"]
            elif "geom" in payload:
                rows = [payload]
        elif isinstance(payload, list):
            rows = payload

        for row in rows:
            if not isinstance(row, dict):
                continue
            msg = str(row.get("message", "")).strip().lower()
            if msg.startswith("204"):
                continue
            geom_text = row.get("geom")
            if isinstance(geom_text, str) and geom_text.strip():
                wkts.append(geom_text.strip())

        if wkts:
            geoms = []
            for geom_text in wkts:
                try:
                    geoms.append(wkt.loads(geom_text))
                except Exception:
                    continue
            if geoms:
                merged = unary_union(geoms)
                if isinstance(merged, Polygon):
                    return merged
                if isinstance(merged, MultiPolygon):
                    return max(merged.geoms, key=lambda g: g.area) if merged.geoms else None

        # Fallback to generic extractors for alternative payload shape
        geometry = self._extract_geometry(payload)
        if not geometry:
            return None
        return self._geometry_to_polygon(geometry)

    def _resolve_coordinates(self, inp: dict) -> GeocodingResult:
        """Build a buffer polygon around a lat/lon pair."""
        lat = inp["latitude"]
        lon = inp["longitude"]
        radius = inp.get("buffer_m", 500.0)

        poly = self._create_buffer_polygon(lat, lon, radius_m=radius)
        area = self._compute_area(poly)

        return GeocodingResult(
            polygon=poly,
            centroid_lat=lat,
            centroid_lon=lon,
            area_sqm=area,
            source="manual",
            confidence=1.0,
            raw_input=f"{lat},{lon}",
        )

    def _create_buffer_polygon(self, lat: float, lon: float, radius_m: float) -> Polygon:
        """Create a circle polygon around a point with meter-accurate radius."""
        point_wgs = Point(lon, lat)
        point_utm = transform(self._to_utm, point_wgs)
        buffer_utm = point_utm.buffer(radius_m, resolution=64)
        buffer_wgs = transform(self._to_wgs, buffer_utm)
        return buffer_wgs

    def _compute_area(self, polygon: Polygon) -> float:
        """Compute area in square meters via UTM projection."""
        utm_poly = transform(self._to_utm, polygon)
        return utm_poly.area

    def _geometry_to_polygon(self, geometry_obj: Any) -> Optional[Polygon]:
        """Convert various geometry payload shapes into a Polygon."""
        if not geometry_obj:
            return None

        geom = None

        if isinstance(geometry_obj, str):
            # Try JSON first, then WKT
            try:
                geom = shape(json.loads(geometry_obj))
            except Exception:
                try:
                    geom = wkt.loads(geometry_obj)
                except Exception:
                    return None
        elif isinstance(geometry_obj, dict):
            if geometry_obj.get("type") == "Feature":
                feature_geom = geometry_obj.get("geometry")
                if feature_geom:
                    geom = shape(feature_geom)
            elif geometry_obj.get("type") == "FeatureCollection":
                features = geometry_obj.get("features") or []
                if features and features[0].get("geometry"):
                    geom = shape(features[0]["geometry"])
            elif geometry_obj.get("type") and geometry_obj.get("coordinates") is not None:
                geom = shape(geometry_obj)
        else:
            return None

        if geom is None:
            return None
        if isinstance(geom, Polygon):
            return geom
        if isinstance(geom, MultiPolygon):
            # Use largest piece if multipolygon.
            return max(geom.geoms, key=lambda g: g.area) if geom.geoms else None

        # Last fallback: convex hull if area geometry.
        hull = geom.convex_hull
        return hull if isinstance(hull, Polygon) else None

    def _extract_geometry(self, data: Any) -> Optional[Any]:
        """
        Try to discover geometry payload in unknown KGIS response formats.
        Looks for common keys recursively.
        """
        if data is None:
            return None

        if isinstance(data, str):
            try:
                return self._extract_geometry(json.loads(data))
            except Exception:
                return data

        if isinstance(data, list):
            for item in data:
                found = self._extract_geometry(item)
                if found is not None:
                    return found
            return None

        if isinstance(data, dict):
            # Direct geometry object
            if data.get("type") and data.get("coordinates") is not None:
                return data
            if data.get("type") in {"Feature", "FeatureCollection"}:
                return data

            common_keys = (
                "geometry",
                "geojson",
                "geom",
                "shape",
                "polygon",
                "wkt",
            )
            for key in common_keys:
                if key in data and data[key]:
                    found = self._extract_geometry(data[key])
                    if found is not None:
                        return found

            # Generic recursive walk
            for value in data.values():
                found = self._extract_geometry(value)
                if found is not None:
                    return found

        return None

    def _find_key_recursive(self, data: Any, keys: tuple[str, ...]) -> Optional[Any]:
        """Find first matching key value in nested dict/list payload."""
        if isinstance(data, dict):
            for key in keys:
                if key in data and data[key] not in (None, "", []):
                    return data[key]
            for value in data.values():
                found = self._find_key_recursive(value, keys)
                if found is not None:
                    return found
            return None
        if isinstance(data, list):
            for item in data:
                found = self._find_key_recursive(item, keys)
                if found is not None:
                    return found
        return None
