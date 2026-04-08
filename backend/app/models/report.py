"""
SQLAlchemy ORM models for safety reports and legal flags.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SafetyReport(Base):
    """
    Final consolidated safety report for a parcel request.
    """
    __tablename__ = "safety_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Risk classification
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_confidence = Column(Float, nullable=False)           # 0–1
    risk_score_raw = Column(Float, nullable=False)            # raw model probability

    # SHAP feature importances (JSON dict: layer_name → shap_value)
    shap_values = Column(JSON, nullable=True)

    # Spatial scores used as features
    spatial_scores = Column(JSON, nullable=False)             # {layer: score}

    # LLM-generated plain-language summary
    plain_language_summary = Column(Text, nullable=True)
    recommended_next_steps = Column(JSON, nullable=True)      # list of strings

    # Export paths
    pdf_path = Column(String(500), nullable=True)
    shareable_token = Column(String(64), nullable=True, unique=True)

    # Metadata
    processing_time_ms = Column(Integer, nullable=True)
    model_version = Column(String(20), default="1.0.0")


class LegalFlag(Base):
    """
    Individual legal / environmental flag raised against a parcel.
    One row per flag per report.
    """
    __tablename__ = "legal_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    flag_code = Column(String(30), nullable=False)            # e.g. "WATERBODY_BUFFER_VIOLATION"
    flag_category = Column(String(50), nullable=False)        # "environmental" | "legal" | "revenue"
    flag_label = Column(String(200), nullable=False)          # short title
    description = Column(Text, nullable=False)                # plain-text description
    severity = Column(String(20), nullable=False)             # "critical" | "high" | "medium" | "low"

    # Legal citation
    act_name = Column(String(300), nullable=True)             # e.g. "Karnataka Land Revenue Act, 1964"
    act_section = Column(String(100), nullable=True)          # e.g. "Section 76A"
    clause_summary = Column(Text, nullable=True)              # brief clause summary

    # Spatial context
    layer_name = Column(String(100), nullable=True)           # which KGIS layer triggered this
    overlap_pct = Column(Float, nullable=True)
    nearest_dist_m = Column(Float, nullable=True)
