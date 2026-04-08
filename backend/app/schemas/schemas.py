"""
Pydantic schemas — request & response models for the GeoSafe API.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
import uuid


# ━━━━━━━━━━━━━━━━━━ REQUEST SCHEMAS ━━━━━━━━━━━━━━━━━━

class SurveyNumberInput(BaseModel):
    """Input: Karnataka survey number with location details."""
    district: str = Field(..., min_length=1, examples=["Bengaluru Urban"])
    taluk: str = Field(..., min_length=1, examples=["Anekal"])
    hobli: Optional[str] = Field(None, examples=["Kasaba"])
    village: str = Field(..., min_length=1, examples=["Sarjapura"])
    village_code: Optional[str] = Field(None, examples=["0201020003"])
    survey_number: str = Field(..., min_length=1, examples=["45/1"])
    latitude: Optional[float] = Field(None, ge=-90, le=90, examples=[12.8633])
    longitude: Optional[float] = Field(None, ge=-180, le=180, examples=[77.6130])


class CoordinatesInput(BaseModel):
    """Input: latitude/longitude (WGS-84)."""
    latitude: float = Field(..., ge=-90, le=90, examples=[12.8584])
    longitude: float = Field(..., ge=-180, le=180, examples=[77.7842])
    buffer_m: float = Field(500.0, ge=50, le=5000, description="Buffer radius in metres for parcel approximation")


class ValidationRequest(BaseModel):
    """Top-level request — either a survey number or coordinates."""
    input_type: Literal["survey_number", "coordinates"]
    survey_input: Optional[SurveyNumberInput] = None
    coordinates_input: Optional[CoordinatesInput] = None


# ━━━━━━━━━━━━━━━━━━ RESPONSE SCHEMAS ━━━━━━━━━━━━━━━━━━

class ParcelInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    input_type: str
    raw_input: str
    district: Optional[str] = None
    taluk: Optional[str] = None
    village: Optional[str] = None
    survey_number: Optional[str] = None
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    area_sqm: Optional[float] = None
    geocode_source: Optional[str] = None
    geocode_confidence: Optional[float] = None


class LayerValidation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    layer_name: str
    layer_label: Optional[str] = None
    intersects: bool
    overlap_area_sqm: float = 0.0
    overlap_pct: float = 0.0
    buffer_distance_m: float = 0.0
    nearest_feature_dist_m: Optional[float] = None
    spatial_score: float = 0.0


class LegalFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flag_code: str
    flag_category: str
    flag_label: str
    description: str
    severity: str
    act_name: Optional[str] = None
    act_section: Optional[str] = None
    clause_summary: Optional[str] = None
    layer_name: Optional[str] = None
    overlap_pct: Optional[float] = None


class ShapExplanation(BaseModel):
    """Individual SHAP feature importance."""
    feature_name: str
    shap_value: float
    direction: str          # "increases_risk" | "decreases_risk"
    human_label: str        # e.g. "Water Body Proximity"


class SafetyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID
    generated_at: datetime

    # Parcel
    parcel: ParcelInfo

    # Risk
    risk_level: str         # "LOW" | "MEDIUM" | "HIGH"
    risk_confidence: float
    risk_score_raw: float

    # Spatial validations
    layer_validations: list[LayerValidation]

    # Legal flags
    legal_flags: list[LegalFlagResponse]

    # SHAP
    shap_explanations: list[ShapExplanation] = []

    # LLM
    plain_language_summary: Optional[str] = None
    recommended_next_steps: list[str] = []

    # Export
    pdf_url: Optional[str] = None
    shareable_link: Optional[str] = None

    processing_time_ms: Optional[int] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    db_connected: bool
    kgis_reachable: bool
