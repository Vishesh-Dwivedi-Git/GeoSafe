"""
Step 2 - KGIS Layer Fetch (Web API Only)

This service intentionally avoids WFS and fetches risk-layer assets
from KGIS Nearby Assets Web API only.
"""
import logging
from shapely.geometry import Polygon, mapping, box, Point
from shapely.ops import transform
from pyproj import Transformer

from app.config import get_settings
from app.services.kgis_webapi import KGISWebAPIService

logger = logging.getLogger(__name__)
settings = get_settings()


KGIS_LAYERS = {
    "water_bodies": {
        "label": "Water Bodies & Lake Boundaries",
        "source": "kgis_webapi",
        "buffer_m": 200,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_WATER_BODIES,
    },
    "forest_areas": {
        "label": "Forest & Eco-Sensitive Zones",
        "source": "kgis_webapi",
        "buffer_m": 500,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_FOREST,
    },
    "eco_sensitive_zones": {
        "label": "Eco-Sensitive Zones (ESZ)",
        "source": "kgis_webapi",
        "buffer_m": 300,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_ECO_SENSITIVE,
    },
    "flood_zones": {
        "label": "Flood-Prone Zones",
        "source": "kgis_webapi",
        "buffer_m": 100,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_FLOOD,
    },
    "govt_land": {
        "label": "Government-Acquired Land",
        "source": "kgis_webapi",
        "buffer_m": 0,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_GOVT_LAND,
    },
    "revenue_land": {
        "label": "Revenue Land Records",
        "source": "kgis_webapi",
        "buffer_m": 0,
        "nearby_asset_code": settings.KGIS_NEARBY_ASSET_CODE_REVENUE_LAND,
    },
}

# Kept for compatibility with routes listing endpoint.
BHUVAN_LAYERS: dict = {}


class KGISFetchResult:
    """Container for one fetched layer's GeoJSON."""

    def __init__(
        self,
        layer_name: str,
        layer_label: str,
        source: str,
        buffer_m: float,
        geojson: dict,
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
    """Fetch KGIS layer assets via Nearby Assets API only."""

    def __init__(self):
        self._kgis_webapi = KGISWebAPIService()
        self._to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True).transform

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
        bbox_wkt = box(*bbox).wkt

        centroid = parcel_polygon.centroid
        lat = centroid.y
        lon = centroid.x

        results: list[KGISFetchResult] = []
        for name, layer_cfg in KGIS_LAYERS.items():
            geojson = {"type": "FeatureCollection", "features": []}
            layer_code = layer_cfg.get("nearby_asset_code")
            if layer_code:
                geojson = await self._fetch_nearby_assets_layer(
                    layer_code=str(layer_code),
                    latitude=lat,
                    longitude=lon,
                    buffer_m=float(layer_cfg["buffer_m"]),
                )

            results.append(
                KGISFetchResult(
                    layer_name=name,
                    layer_label=layer_cfg["label"],
                    source="kgis_webapi",
                    buffer_m=layer_cfg["buffer_m"],
                    geojson=geojson,
                    feature_count=len(geojson.get("features", [])),
                    bbox_wkt=bbox_wkt,
                )
            )

        logger.info(
            "Fetched %d KGIS WebAPI layers - total features: %d",
            len(results),
            sum(r.feature_count for r in results),
        )
        return results

    async def _fetch_nearby_assets_layer(
        self,
        layer_code: str,
        latitude: float,
        longitude: float,
        buffer_m: float,
    ) -> dict:
        """
        Converts Nearby Assets point results into tiny polygons so the
        existing spatial engine can compute intersects/overlap/proximity.
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

                # NearbyAssets may return DD or UTM-like XY.
                if abs(x_val) <= 180 and abs(y_val) <= 90:
                    lon, lat = x_val, y_val
                else:
                    p = transform(self._to_wgs, Point(x_val, y_val))
                    lon, lat = p.x, p.y

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
        except Exception as e:
            logger.warning("NearbyAssets fetch failed for layer_code=%s: %s", layer_code, e)
            return {"type": "FeatureCollection", "features": []}

    @staticmethod
    def generate_demo_layers(parcel_polygon: Polygon) -> list[KGISFetchResult]:
        """
        Optional demo generator retained for development fallback mode.
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
            for name, cfg in KGIS_LAYERS.items()
        ]
