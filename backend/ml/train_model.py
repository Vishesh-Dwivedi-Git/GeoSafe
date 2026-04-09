"""
Training script for the AI land risk model.

Outputs:
  - ml/model.pkl for the new analyze-land endpoint
"""
from __future__ import annotations

import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

FEATURE_NAMES = [
    "distance_to_water",
    "water_overlap_percentage",
    "inside_forest",
    "inside_esz",
    "flood_risk_score",
    "govt_land_overlap",
]
RISK_LABELS = ["LOW", "MEDIUM", "HIGH"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


def generate_synthetic_data(n_samples: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)

    distance_to_water = rng.uniform(0, 1000, size=n_samples)
    water_overlap_percentage = rng.uniform(0, 100, size=n_samples)
    inside_forest = rng.binomial(1, 0.12, size=n_samples)
    inside_esz = rng.binomial(1, 0.08, size=n_samples)
    flood_risk_score = rng.uniform(0, 1, size=n_samples)
    govt_land_overlap = rng.uniform(0, 1, size=n_samples)

    X = np.column_stack(
        [
            distance_to_water,
            water_overlap_percentage,
            inside_forest,
            inside_esz,
            flood_risk_score,
            govt_land_overlap,
        ]
    )

    y = np.zeros(n_samples, dtype=int)
    for idx, row in enumerate(X):
        risk_score = 0.0
        risk_score += max(0.0, 1.0 - min(row[0], 500) / 500.0) * 0.15
        risk_score += min(row[1] / 100.0, 1.0) * 0.2
        risk_score += row[2] * 0.25
        risk_score += row[3] * 0.35
        risk_score += row[4] * 0.2
        risk_score += row[5] * 0.25

        if row[3] == 1 or row[2] == 1:
            risk_score += 0.15

        if risk_score >= 0.75:
            y[idx] = 2
        elif risk_score >= 0.38:
            y[idx] = 1
        else:
            y[idx] = 0

    noise_mask = rng.random(n_samples) < 0.04
    y[noise_mask] = rng.integers(0, 3, size=noise_mask.sum())
    return X, y


def train() -> None:
    print("Training GeoSafe AI land model")
    print(f"Features: {FEATURE_NAMES}")

    X, y = generate_synthetic_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    print(classification_report(y_test, predictions, target_names=RISK_LABELS))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    train()
