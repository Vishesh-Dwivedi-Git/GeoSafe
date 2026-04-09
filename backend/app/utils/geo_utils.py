"""
Geospatial helper utilities shared by AI analysis services.
"""
from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import GeometryCollection, shape, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

WGS84 = "EPSG:4326"
UTM_43N = "EPSG:32643"

_TO_UTM = Transformer.from_crs(WGS84, UTM_43N, always_xy=True).transform
_TO_WGS = Transformer.from_crs(UTM_43N, WGS84, always_xy=True).transform


def to_utm(geometry: BaseGeometry) -> BaseGeometry:
    return transform(_TO_UTM, geometry)


def to_wgs84(geometry: BaseGeometry) -> BaseGeometry:
    return transform(_TO_WGS, geometry)


def area_sqm(geometry: BaseGeometry) -> float:
    return to_utm(geometry).area


def distance_m(geometry_a: BaseGeometry, geometry_b: BaseGeometry) -> float:
    return to_utm(geometry_a).distance(to_utm(geometry_b))


def feature_collection_from_geometries(
    geometries: list[BaseGeometry],
    properties: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for index, geometry in enumerate(geometries):
        if geometry.is_empty:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": (properties[index] if properties and index < len(properties) else {}),
                "geometry": mapping(geometry),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def feature_collection_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for record in records:
        geometry = record.get("geometry")
        if geometry is None:
            continue
        if isinstance(geometry, BaseGeometry):
            geom = geometry
        else:
            geom = shape(geometry)
        props = {key: value for key, value in record.items() if key != "geometry"}
        features.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})
    return {"type": "FeatureCollection", "features": features}


def normalize_geometry_collection(geometry: BaseGeometry) -> list[BaseGeometry]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, GeometryCollection):
        return [geom for geom in geometry.geoms if not geom.is_empty]
    if hasattr(geometry, "geoms") and geometry.geom_type.startswith("Multi"):
        return [geom for geom in geometry.geoms if not geom.is_empty]
    return [geometry]
