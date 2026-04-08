"""
KGIS Web API Client

Uses documented KGIS web API endpoints:
  https://kgis.ksrsac.in/kgis/webapi.aspx
Base:
  https://kgis.ksrsac.in:9000/genericwebservices/ws
"""
from __future__ import annotations

import logging
import json
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class KGISWebAPIService:
    """Thin client for KGIS JSON web APIs."""

    def __init__(self):
        self.base_url = settings.KGIS_WEBAPI_BASE_URL.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0, follow_redirects=True)

    @staticmethod
    def _summarize_payload(data: Any, max_len: int = 900) -> str:
        """Compact payload preview for logs."""
        try:
            text = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
        except Exception:
            text = str(data)
        if len(text) > max_len:
            return f"{text[:max_len]}...<truncated {len(text) - max_len} chars>"
        return text

    @staticmethod
    def _has_data(payload: dict[str, Any]) -> bool:
        if not payload:
            return False

        # Explicit service-shaped responses
        if isinstance(payload.get("surveynumber"), list):
            return len(payload["surveynumber"]) > 0
        if isinstance(payload.get("adminhierarchy"), list) and payload.get("surveynumber") is not None:
            return len(payload["adminhierarchy"]) > 0 or len(payload.get("surveynumber", [])) > 0

        items = payload.get("items")
        if isinstance(items, list) and items:
            for item in items:
                if isinstance(item, dict):
                    msg = str(item.get("message", "")).lower()
                    if msg and ("not available" in msg or msg.startswith("204")):
                        continue
                    if item.get("geom"):
                        return True
                return True
            return False
        if isinstance(items, dict):
            return True
        return False

    @staticmethod
    def _name_variants(raw: str) -> list[str]:
        """
        Generate practical value variants for KGIS strict-name endpoints.
        Example: Bengaluru(Urban) -> Bengaluru (Urban), Bengaluru Urban, etc.
        """
        if not raw:
            return []
        text = " ".join(raw.strip().split())
        variants = [
            text,
            text.replace("(", " (").replace(")", ")"),
            text.replace(" (", "(").replace(") ", ")"),
            text.replace("(Urban)", " (Urban)").replace("(Rural)", " (Rural)"),
            text.replace("Bangalore", "Bengaluru"),
            text.replace("Bengaluru", "Bangalore"),
            text.replace("-", " "),
            text.replace(" ", "-"),
        ]
        # unique, preserve order
        out: list[str] = []
        for variant in variants:
            value = " ".join(variant.split())
            if value and value not in out:
                out.append(value)
        return out

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info(
            "KGIS API %s params=%s status=%s payload=%s",
            path,
            params,
            response.status_code,
            self._summarize_payload(data),
        )
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            return data
        return {"raw": data}

    async def _get_raw(self, absolute_url: str, params: dict[str, Any]) -> Any:
        response = await self._client.get(absolute_url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info(
            "KGIS API ABS %s params=%s status=%s payload=%s",
            absolute_url,
            params,
            response.status_code,
            self._summarize_payload(data),
        )
        return data

    async def _post_raw(self, absolute_url: str, json_payload: Any) -> Any:
        response = await self._client.post(absolute_url, json=json_payload)
        response.raise_for_status()
        data = response.json()
        logger.info(
            "KGIS API ABS %s method=POST status=%s payload=%s",
            absolute_url,
            response.status_code,
            self._summarize_payload(data),
        )
        return data

    async def nearby_admin_hierarchy(
        self, latitude: float, longitude: float, distance_m: int = 1000, aoi: str = "d,t,h"
    ) -> dict[str, Any]:
        """Get district/taluk/hobli around coordinates."""
        return await self._get(
            "nearbyadminhierarchy",
            {
                "coordinates": f"{latitude},{longitude}",
                "distance": distance_m,
                "type": "DD",
                "aoi": aoi,
            },
        )

    async def survey_numbers(
        self,
        village_code: str,
        latitude: float,
        longitude: float,
        distance_m: int = 1000,
    ) -> dict[str, Any]:
        """Get survey numbers around coordinate for a village code."""
        return await self._get(
            "surveyno",
            {
                "villagecode": village_code,
                "coordinates": f"{latitude},{longitude}",
                "type": "DD",
                "distance": distance_m,
            },
        )

    async def district_code(self, district_name: str) -> dict[str, Any]:
        """Resolve KGIS district code from district name."""
        last = {"items": []}
        for variant in self._name_variants(district_name):
            data = await self._get("districtcode", {"districtname": variant})
            last = data
            if self._has_data(data):
                return data
        return last

    async def taluk_code(self, taluk_name: str) -> dict[str, Any]:
        """Resolve KGIS taluk code from taluk name."""
        last = {"items": []}
        for variant in self._name_variants(taluk_name):
            data = await self._get("talukcode", {"talukname": variant})
            last = data
            if self._has_data(data):
                return data
        return last

    async def hobli_code(self, hobli_name: str) -> dict[str, Any]:
        """Resolve KGIS hobli code from hobli name."""
        last = {"items": []}
        for variant in self._name_variants(hobli_name):
            data = await self._get("hoblicode", {"hobliname": variant})
            last = data
            if self._has_data(data):
                return data
        return last

    async def location_details(self, latitude: float, longitude: float, aoi: str = "w") -> dict[str, Any]:
        """
        Get village/admin details from coordinates.
        Uses documented endpoint: /getlocationdetails?coordinates=lat,lon&type=dd&aoi=w
        """
        return await self._get(
            "getlocationdetails",
            {
                "coordinates": f"{latitude},{longitude}",
                "type": "dd",
                "aoi": aoi,
            },
        )

    async def nearby_assets(
        self,
        layer_code: str,
        latitude: float,
        longitude: float,
        number: int = 5,
        coord_type: str = "DD",
    ) -> dict[str, Any]:
        """
        Nearby Assets API:
        https://kgis.ksrsac.in:9000/NearbyAssets/ws/getNearbyAssetData?code=...&coordinates=...&type=DD|UTM&number=...
        """
        url = f"{settings.KGIS_NEARBY_ASSETS_BASE_URL.rstrip('/')}/getNearbyAssetData"
        data = await self._get_raw(
            url,
            {
                "code": layer_code,
                "coordinates": f"{latitude},{longitude}",
                "type": coord_type,
                "number": number,
            },
        )
        if isinstance(data, list):
            return {"items": data}
        if isinstance(data, dict):
            return data
        return {"raw": data}

    async def admin_codes2(self, points: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Zonation API:
        https://kgis.ksrsac.in:9000/genericwebservices/ws/getKGISAdminCodes2  (POST)
        """
        url = f"{self.base_url}/getKGISAdminCodes2"
        data = await self._post_raw(url, points)
        if isinstance(data, dict):
            return data
        return {"raw": data}

    async def geometric_polygon_area(
        self,
        village_code: str,
        survey_number: str,
    ) -> dict[str, Any]:
        """
        Fetch geometry for a survey.

        KGIS docs show:
          /geomForSurveyNum/{village_code}/{survey_number}/DD
        Some deployments may expose alternate names, so we keep a fallback.
        """
        candidates = [
            (f"geomForSurveyNum/{village_code}/{survey_number}/DD", {}),
            (f"geomForSurveyNum/{village_code}/{survey_number}/UTM", {}),
            ("geometricpolygonarea", {"villagecode": village_code, "surveyno": survey_number}),
        ]
        last: dict[str, Any] = {}
        for path, params in candidates:
            try:
                data = await self._get(path, params)
                last = data
                if self._has_data(data):
                    return data
            except Exception:
                continue
        return last

    async def check_services(
        self,
        latitude: float = 12.9716,
        longitude: float = 77.5946,
        village_code: Optional[str] = None,
        survey_number: Optional[str] = None,
        district_name: Optional[str] = None,
        taluk_name: Optional[str] = None,
        hobli_name: Optional[str] = None,
        nearby_asset_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Health-style checker for the KGIS web APIs used by this project."""
        checks: dict[str, Any] = {
            "base_url": self.base_url,
            "nearby_admin_hierarchy": {"ok": False},
            "district_code": {"ok": False, "skipped": district_name is None},
            "taluk_code": {"ok": False, "skipped": taluk_name is None},
            "hobli_code": {"ok": False, "skipped": hobli_name is None},
            "surveyno": {"ok": False, "skipped": village_code is None},
            "geometric_polygon_area": {
                "ok": False,
                "skipped": village_code is None or survey_number is None,
            },
            "nearby_assets": {"ok": False, "skipped": nearby_asset_code is None},
            "admin_codes2": {"ok": False},
        }

        try:
            data = await self.nearby_admin_hierarchy(latitude, longitude)
            items = data.get("items", []) if isinstance(data, dict) else []
            checks["nearby_admin_hierarchy"] = {
                "ok": True,
                "sample_count": len(items) if isinstance(items, list) else 0,
                "sample": (items[0] if items else {}),
            }
        except Exception as exc:
            checks["nearby_admin_hierarchy"] = {"ok": False, "error": str(exc)}

        if district_name:
            try:
                data = await self.district_code(district_name)
                checks["district_code"] = {"ok": True, "sample": data}
            except Exception as exc:
                checks["district_code"] = {"ok": False, "error": str(exc)}

        if taluk_name:
            try:
                data = await self.taluk_code(taluk_name)
                checks["taluk_code"] = {"ok": True, "sample": data}
            except Exception as exc:
                checks["taluk_code"] = {"ok": False, "error": str(exc)}

        if hobli_name:
            try:
                data = await self.hobli_code(hobli_name)
                checks["hobli_code"] = {"ok": True, "sample": data}
            except Exception as exc:
                checks["hobli_code"] = {"ok": False, "error": str(exc)}

        if village_code:
            try:
                data = await self.survey_numbers(village_code, latitude, longitude)
                checks["surveyno"] = {
                    "ok": True,
                    "sample_count": len(data.get("items", [])) if "items" in data else 1,
                    "sample": (data.get("items", [{}])[0] if "items" in data else data),
                }
            except Exception as exc:
                checks["surveyno"] = {"ok": False, "error": str(exc)}

        if village_code and survey_number:
            try:
                data = await self.geometric_polygon_area(village_code, survey_number)
                checks["geometric_polygon_area"] = {
                    "ok": True,
                    "has_payload": bool(data),
                }
            except Exception as exc:
                checks["geometric_polygon_area"] = {"ok": False, "error": str(exc)}

        if nearby_asset_code:
            try:
                data = await self.nearby_assets(nearby_asset_code, latitude, longitude, number=5, coord_type="DD")
                items = data.get("items", []) if isinstance(data, dict) else []
                checks["nearby_assets"] = {
                    "ok": True,
                    "sample_count": len(items),
                    "sample": items[0] if items else {},
                }
            except Exception as exc:
                checks["nearby_assets"] = {"ok": False, "error": str(exc)}

        try:
            payload = [{"ID": 1, "Gps_Lat": latitude, "Gps_Lon": longitude}]
            data = await self.admin_codes2(payload)
            checks["admin_codes2"] = {
                "ok": True,
                "statusCode": data.get("statusCode"),
                "count": data.get("count"),
                "sample": (data.get("dataList", [{}])[0] if isinstance(data.get("dataList"), list) else {}),
            }
        except Exception as exc:
            checks["admin_codes2"] = {"ok": False, "error": str(exc)}

        return checks
