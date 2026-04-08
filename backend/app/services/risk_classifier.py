"""
Step 4 — Risk Classifier (AI Model)

A Random Forest classifier trained on labelled parcel data.
- Features: 5 spatial_scores (one per KGIS layer)
- Output: Low / Medium / High risk
- SHAP: per-prediction feature importance for explainability

In production, the trained model is loaded from disk.
For development, a rule-based fallback is provided.
"""
import logging
import os
import pickle
from typing import Optional
import numpy as np

from app.config import get_settings
from app.services.spatial_validation import SpatialValidationScore

logger = logging.getLogger(__name__)
settings = get_settings()

# Feature order must match training
FEATURE_NAMES = [
    "water_bodies",
    "forest_areas",
    "eco_sensitive_zones",
    "flood_zones",
    "govt_land",
]

RISK_LABELS = ["LOW", "MEDIUM", "HIGH"]


class RiskPrediction:
    """Output of the risk classifier."""
    def __init__(
        self,
        risk_level: str,
        confidence: float,
        raw_score: float,
        shap_values: dict[str, float],
        feature_vector: dict[str, float],
    ):
        self.risk_level = risk_level
        self.confidence = confidence
        self.raw_score = raw_score
        self.shap_values = shap_values
        self.feature_vector = feature_vector


class RiskClassifierService:
    """
    Wraps a scikit-learn Random Forest + SHAP explainer.
    Falls back to heuristic rules when no trained model exists.
    """

    def __init__(self):
        self._model = None
        self._shap_explainer = None
        self._label_encoder = None
        self._load_model()

    def _load_model(self):
        """Attempt to load pre-trained model from disk."""
        model_path = settings.ML_MODEL_PATH
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    self._model = pickle.load(f)
                logger.info("Loaded risk classifier from %s", model_path)
            except Exception as e:
                logger.warning("Error loading model: %s", e)

        shap_path = settings.SHAP_EXPLAINER_PATH
        if os.path.exists(shap_path):
            try:
                with open(shap_path, "rb") as f:
                    self._shap_explainer = pickle.load(f)
                logger.info("Loaded SHAP explainer from %s", shap_path)
            except Exception as e:
                logger.warning("Error loading SHAP explainer: %s", e)

    def predict(
        self,
        validation_scores: list[SpatialValidationScore],
    ) -> RiskPrediction:
        """
        Predict risk level from spatial validation scores.
        Uses the trained model if available, else a rule-based fallback.
        """
        # Build feature vector in canonical order
        score_map = {s.layer_name: s.spatial_score for s in validation_scores}
        feature_vector = {name: score_map.get(name, 0.0) for name in FEATURE_NAMES}
        features = np.array([[feature_vector[n] for n in FEATURE_NAMES]])

        if self._model is not None:
            return self._predict_ml(features, feature_vector)
        else:
            return self._predict_heuristic(features, feature_vector, validation_scores)

    def _predict_ml(
        self, features: np.ndarray, feature_vector: dict
    ) -> RiskPrediction:
        """Prediction via trained Random Forest + SHAP."""
        probas = self._model.predict_proba(features)[0]
        pred_idx = int(np.argmax(probas))
        risk_level = RISK_LABELS[pred_idx]
        confidence = float(probas[pred_idx])

        # SHAP values
        shap_values = {}
        if self._shap_explainer is not None:
            try:
                sv = self._shap_explainer.shap_values(features)
                # sv is [n_classes][n_samples][n_features] for RandomForest
                if isinstance(sv, list):
                    shap_for_class = sv[pred_idx][0]
                else:
                    shap_for_class = sv[0]
                shap_values = {
                    name: round(float(val), 4)
                    for name, val in zip(FEATURE_NAMES, shap_for_class)
                }
            except Exception as e:
                logger.warning("SHAP computation failed: %s", e)

        # Raw score = weighted average of risk probabilities
        raw_score = float(probas[1] * 0.5 + probas[2] * 1.0)

        return RiskPrediction(
            risk_level=risk_level,
            confidence=confidence,
            raw_score=round(raw_score, 4),
            shap_values=shap_values,
            feature_vector=feature_vector,
        )

    def _predict_heuristic(
        self,
        features: np.ndarray,
        feature_vector: dict,
        validation_scores: list[SpatialValidationScore],
    ) -> RiskPrediction:
        """
        Rule-based risk classification (when no ML model is present):
          - Any layer score ≥ 0.7 → HIGH
          - Any layer score ≥ 0.4 or mean score ≥ 0.3 → MEDIUM
          - Otherwise → LOW
        """
        scores = features[0]
        max_score = float(np.max(scores))
        mean_score = float(np.mean(scores))

        # Map overlap/intersection data for extra context
        any_direct_overlap = any(
            s.intersects and s.overlap_pct > 20
            for s in validation_scores
            if s.layer_name in ["eco_sensitive_zones", "govt_land", "forest_areas"]
        )

        if max_score >= 0.7 or any_direct_overlap:
            risk_level = "HIGH"
            confidence = min(0.95, 0.6 + max_score * 0.3)
        elif max_score >= 0.4 or mean_score >= 0.3:
            risk_level = "MEDIUM"
            confidence = min(0.85, 0.5 + mean_score * 0.3)
        else:
            risk_level = "LOW"
            confidence = min(0.95, 0.7 + (1.0 - max_score) * 0.2)

        # Simulate SHAP-like importance
        total = sum(abs(v) for v in scores) or 1.0
        shap_values = {
            name: round(float(val / total), 4)
            for name, val in zip(FEATURE_NAMES, scores)
        }

        raw_score = round(max_score * 0.6 + mean_score * 0.4, 4)

        return RiskPrediction(
            risk_level=risk_level,
            confidence=round(confidence, 4),
            raw_score=raw_score,
            shap_values=shap_values,
            feature_vector=feature_vector,
        )
