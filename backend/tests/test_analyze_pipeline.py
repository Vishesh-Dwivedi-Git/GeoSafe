import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from shapely.geometry import Point

from app.main import app
from app.services.analyze_service import analyze_service
from app.services.geocoding import GeocodingResult


def make_land_result(lat: float = 12.9716, lng: float = 77.5946, radius_deg: float = 0.002) -> GeocodingResult:
    polygon = Point(lng, lat).buffer(radius_deg)
    return GeocodingResult(
        polygon=polygon,
        centroid_lat=lat,
        centroid_lon=lng,
        area_sqm=1000.0,
        source="test",
        confidence=1.0,
        raw_input=f"{lat},{lng}",
    )


class AnalyzePipelineTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self._original_fallback_points = list(analyze_service._layers._fallback_points)

    def tearDown(self):
        analyze_service._layers._fallback_points = self._original_fallback_points
        self.client.__exit__(None, None, None)
        self.client.close()

    def test_near_water_changes_features(self):
        land = make_land_result()
        layers = {
            "water": {"present": True, "distance_m": 18.0, "count": 1},
            "forest": {"present": False, "attributes": {}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }

        with patch.object(analyze_service._kgis, "resolve_land", AsyncMock(return_value=land)), patch.object(
            analyze_service._layers,
            "get_layers",
            AsyncMock(return_value=layers),
        ):
            response = self.client.post(
                "/api/v1/analyze-land",
                json={
                    "input_type": "coordinates",
                    "coordinates_input": {"latitude": land.centroid_lat, "longitude": land.centroid_lon, "buffer_m": 500},
                },
            )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["features"]["water_present"], 1.0)
        self.assertLess(body["features"]["distance_to_water"], 100.0)

    def test_inside_forest_rule_override_high(self):
        land = make_land_result()
        layers = {
            "water": {"present": False, "distance_m": 999999.0, "count": 0},
            "forest": {"present": True, "attributes": {"name": "forest"}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }

        with patch.object(analyze_service._kgis, "resolve_land", AsyncMock(return_value=land)), patch.object(
            analyze_service._layers,
            "get_layers",
            AsyncMock(return_value=layers),
        ):
            response = self.client.post(
                "/api/v1/analyze-land",
                json={
                    "input_type": "coordinates",
                    "coordinates_input": {"latitude": land.centroid_lat, "longitude": land.centroid_lon, "buffer_m": 500},
                },
            )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["risk"], "HIGH")
        self.assertEqual(body["features"]["forest_present"], 1.0)
        self.assertTrue(body["bhuvan_hits"]["forest"])

    def test_safe_area_returns_valid_response(self):
        land = make_land_result()
        layers = {
            "water": {"present": False, "distance_m": 999999.0, "count": 0},
            "forest": {"present": False, "attributes": {}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }

        with patch.object(analyze_service._kgis, "resolve_land", AsyncMock(return_value=land)), patch.object(
            analyze_service._layers,
            "get_layers",
            AsyncMock(return_value=layers),
        ):
            response = self.client.post(
                "/api/v1/analyze-land",
                json={
                    "input_type": "coordinates",
                    "coordinates_input": {"latitude": land.centroid_lat, "longitude": land.centroid_lon, "buffer_m": 500},
                },
            )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn(body["risk"], {"LOW", "MEDIUM", "HIGH"})
        self.assertIn("features", body)
        self.assertIn("reasoning", body)
        self.assertIn("bhuvan_hits", body)

    def test_nearest_fallback_coordinate_can_fill_missing_hits(self):
        land = make_land_result()
        layers = {
            "water": {"present": False, "distance_m": 999999.0, "count": 0},
            "forest": {"present": False, "attributes": {}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }
        analyze_service._layers._fallback_points = [
            {
                "name": "Test Fallback",
                "latitude": land.centroid_lat,
                "longitude": land.centroid_lon,
                "radius_m": 1000,
                "layers": {"forest": True, "water": True},
                "water_distance_m": 42,
                "attributes": {"forest": {"label": "Fallback forest"}},
            }
        ]
        merged = analyze_service._layers._apply_fallback_points(land.centroid_lat, land.centroid_lon, layers)
        self.assertTrue(merged["forest"]["present"])
        self.assertTrue(merged["water"]["present"])
        self.assertEqual(merged["water"]["distance_m"], 42.0)
        analyze_service._layers._fallback_points = []

    def test_karnataka_heuristic_fallback_marks_western_ghats_risk(self):
        layers = {
            "water": {"present": False, "distance_m": 999999.0, "count": 0},
            "forest": {"present": False, "attributes": {}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }

        merged = analyze_service._layers._apply_karnataka_heuristics(13.34, 75.10, layers)
        self.assertTrue(merged["forest"]["present"])
        self.assertTrue(merged["esz"]["present"])
        self.assertTrue(merged["water"]["present"])
        self.assertGreater(float(merged["flood"].get("score", 0.0)), 0.5)

    def test_karnataka_heuristic_fallback_does_not_apply_outside_state(self):
        layers = {
            "water": {"present": False, "distance_m": 999999.0, "count": 0},
            "forest": {"present": False, "attributes": {}},
            "esz": {"present": False, "attributes": {}},
            "flood": {"present": False, "attributes": {}},
            "government_land": {"present": False, "attributes": {}},
        }

        merged = analyze_service._layers._apply_karnataka_heuristics(19.1, 72.9, layers)
        self.assertFalse(merged["forest"]["present"])
        self.assertFalse(merged["esz"]["present"])
        self.assertFalse(merged["water"]["present"])


if __name__ == "__main__":
    unittest.main()
