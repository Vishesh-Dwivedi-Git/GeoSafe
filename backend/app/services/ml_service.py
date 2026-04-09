"""
ML inference service for AI land analysis.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BACKEND_FEATURE_ORDER = [
    "distance_to_water",
    "water_present",
    "forest_present",
    "esz_present",
    "flood_risk",
    "govt_land_present",
]
FEATURE_ALIASES = {
    "water_overlap": "water_present",
    "inside_forest": "forest_present",
    "inside_esz": "esz_present",
    "flood_risk_score": "flood_risk",
    "govt_land_overlap": "govt_land_present",
}
RISK_LABELS = ["LOW", "MEDIUM", "HIGH"]

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional at runtime until deps are installed
    pd = None


@dataclass
class MLPrediction:
    risk: str
    confidence: float
    scores: dict[str, float]


class HeuristicModel:
    """Fallback model used when a trained artifact is unavailable."""

    def predict(self, rows: list[list[float]]) -> np.ndarray:
        result = []
        for features in rows:
            risk_index = int(np.argmax(self.predict_proba([features])[0]))
            result.append(risk_index)
        return np.array(result)

    def predict_proba(self, rows: list[list[float]]) -> np.ndarray:
        outputs = []
        for distance_to_water, water_overlap, inside_forest, inside_esz, flood_score, govt_overlap in rows:
            high = (
                min(1.0, water_overlap / 100.0) * 0.3
                + inside_forest * 0.25
                + inside_esz * 0.35
                + flood_score * 0.2
                + govt_overlap * 0.3
            )
            if distance_to_water < 50:
                high += 0.1
            medium = max(0.0, 0.45 + flood_score * 0.2 + govt_overlap * 0.15 - high * 0.3)
            low = max(0.0, 1.0 - high - medium)
            probs = np.array([low, medium, high], dtype=float)
            probs = np.clip(probs, 0.001, None)
            outputs.append(probs / probs.sum())
        return np.vstack(outputs)


class MLService:
    """Load the ML model once and serve predictions."""

    def __init__(self):
        self.model: Any = HeuristicModel()
        self.model_path = settings.AI_MODEL_PATH
        self.label_encoder_path = settings.AI_LABEL_ENCODER_PATH
        self.label_encoder: Any | None = None
        self.loaded_from_disk = False
        self.model_feature_order = list(BACKEND_FEATURE_ORDER)

    def load(self) -> None:
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.model_feature_order = self._resolve_model_feature_order()
                self.label_encoder = self._load_label_encoder()
                self.loaded_from_disk = True
                logger.info("Loaded AI model from %s", self.model_path)
                return
            except Exception as exc:
                logger.warning("Failed to load AI model from %s: %s", self.model_path, exc)
        logger.info("Using heuristic fallback model for AI land analysis")

    def predict(self, features: dict[str, float]) -> MLPrediction:
        vector = [float(features.get(self._backend_feature_name(name), 0.0)) for name in self.model_feature_order]
        model_input: Any
        if pd is not None:
            model_input = pd.DataFrame([vector], columns=self.model_feature_order)
        else:
            model_input = [vector]

        probabilities = np.asarray(self.model.predict_proba(model_input)[0], dtype=float)
        prediction = self.model.predict(model_input)[0]
        score_labels = self._score_labels(probabilities)

        if self.label_encoder is not None and not isinstance(prediction, str):
            risk = str(self.label_encoder.inverse_transform([int(prediction)])[0])
        elif isinstance(prediction, str):
            risk = prediction
        else:
            risk = RISK_LABELS[int(prediction)]

        logger.info("Model prediction=%s confidence=%.4f scores=%s", risk, float(np.max(probabilities)), probabilities.tolist())

        return MLPrediction(
            risk=risk,
            confidence=float(np.max(probabilities)),
            scores={label: float(probabilities[idx]) for idx, label in enumerate(score_labels)},
        )

    def _resolve_model_feature_order(self) -> list[str]:
        feature_names = getattr(self.model, "feature_names_in_", None)
        if feature_names is None:
            return list(BACKEND_FEATURE_ORDER)
        return [str(name) for name in feature_names]

    def _load_label_encoder(self) -> Any | None:
        if not os.path.exists(self.label_encoder_path):
            return None
        try:
            encoder = joblib.load(self.label_encoder_path)
            logger.info("Loaded AI label encoder from %s", self.label_encoder_path)
            return encoder
        except Exception as exc:
            logger.warning("Failed to load label encoder from %s: %s", self.label_encoder_path, exc)
            return None

    @staticmethod
    def _backend_feature_name(model_feature_name: str) -> str:
        return FEATURE_ALIASES.get(model_feature_name, model_feature_name)

    def _score_labels(self, probabilities: np.ndarray) -> list[str]:
        if self.label_encoder is not None and hasattr(self.label_encoder, "classes_"):
            return [str(label) for label in self.label_encoder.classes_]
        model_classes = getattr(self.model, "classes_", None)
        if model_classes is not None:
            if self.label_encoder is not None:
                return [str(self.label_encoder.inverse_transform([int(label)])[0]) for label in model_classes]
            if all(isinstance(label, str) for label in model_classes):
                return [str(label) for label in model_classes]
        return list(RISK_LABELS[: len(probabilities)])


ml_service = MLService()
