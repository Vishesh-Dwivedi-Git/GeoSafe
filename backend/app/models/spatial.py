"""
SQLAlchemy ORM models for spatial data — parcels, KGIS layers, validation results.
Uses GeoAlchemy2 for PostGIS geometry columns.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from app.database import Base


class Parcel(Base):
    """
    Represents a land parcel resolved from user input
    (survey number or coordinates). The boundary polygon
    is stored as a PostGIS geometry.
    """
    __tablename__ = "parcels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Input metadata
    input_type = Column(String(20), nullable=False)          # "survey_number" | "coordinates"
    raw_input = Column(Text, nullable=False)                  # original user input string
    district = Column(String(100), nullable=True)
    taluk = Column(String(100), nullable=True)
    hobli = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    survey_number = Column(String(50), nullable=True)

    # Resolved geometry
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    area_sqm = Column(Float, nullable=True)                   # area in square metres
    boundary = Column(Geometry("POLYGON", srid=4326), nullable=True)

    # Geocoding source
    geocode_source = Column(String(50), nullable=True)        # "bhunaksha" | "nominatim" | "manual"
    geocode_confidence = Column(Float, nullable=True)         # 0–1


class KGISLayerCache(Base):
    """
    Cached KGIS / Bhuvan WFS layer features near a parcel,
    so repeated requests don't hammer the external API.
    """
    __tablename__ = "kgis_layer_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    layer_name = Column(String(100), nullable=False)          # e.g. "water_bodies"
    layer_source = Column(String(100), nullable=False)        # "kgis" | "bhuvan" | "osm"
    bbox_wkt = Column(Text, nullable=False)                   # bounding box used for fetch
    feature_count = Column(Integer, default=0)
    geojson = Column(JSON, nullable=False)                    # raw GeoJSON FeatureCollection


class SpatialValidationResult(Base):
    """
    Per-layer spatial validation scores for a parcel.
    One row per (parcel, layer) pair.
    """
    __tablename__ = "spatial_validation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    layer_name = Column(String(100), nullable=False)          # e.g. "water_bodies"
    layer_label = Column(String(150), nullable=True)          # human-readable label
    intersects = Column(Boolean, nullable=False)
    overlap_area_sqm = Column(Float, default=0.0)
    overlap_pct = Column(Float, default=0.0)                  # 0–100 %
    buffer_distance_m = Column(Float, default=0.0)            # buffer used
    nearest_feature_dist_m = Column(Float, nullable=True)     # distance to nearest feature
    spatial_score = Column(Float, default=0.0)                # 0–1 risk contribution
    raw_features = Column(JSON, nullable=True)                # intersecting feature attributes
