"""
ML Model Training Script — Risk Classifier

Trains a Random Forest classifier on synthetic labelled parcel data.
In production, replace synthetic data with real labelled parcels.

Usage:
    python -m ml.train_model

Output:
    ml/models/risk_classifier.pkl
    ml/models/shap_explainer.pkl
"""
import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import shap


FEATURE_NAMES = [
    "water_bodies",
    "forest_areas",
    "eco_sensitive_zones",
    "flood_zones",
    "govt_land",
]

RISK_LABELS = ["LOW", "MEDIUM", "HIGH"]
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def generate_synthetic_data(n_samples: int = 2000) -> tuple:
    """
    Generate synthetic training data.
    Each sample = [water_score, forest_score, esz_score, flood_score, govt_score]
    Label = LOW (0) / MEDIUM (1) / HIGH (2)
    """
    np.random.seed(42)
    X = np.random.rand(n_samples, 5)  # 5 spatial scores [0, 1]

    labels = []
    for row in X:
        max_score = np.max(row)
        mean_score = np.mean(row)

        # HIGH: any critical layer > 0.7, or ESZ/govt > 0.6
        if max_score > 0.7 or row[2] > 0.6 or row[4] > 0.6:
            labels.append(2)  # HIGH
        # MEDIUM: moderate scores
        elif max_score > 0.4 or mean_score > 0.3:
            labels.append(1)  # MEDIUM
        else:
            labels.append(0)  # LOW

    # Add noise (flip ~5% of labels)
    noise_mask = np.random.rand(n_samples) < 0.05
    for i in range(n_samples):
        if noise_mask[i]:
            labels[i] = np.random.randint(0, 3)

    return X, np.array(labels)


def train():
    """Train the Random Forest classifier and SHAP explainer."""
    print("=" * 60)
    print("GeoSafe Risk Classifier — Training Script")
    print("=" * 60)

    # Generate data
    X, y = generate_synthetic_data(3000)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTraining samples : {len(X_train)}")
    print(f"Test samples     : {len(X_test)}")
    print(f"Features         : {FEATURE_NAMES}")
    print(f"Classes          : {RISK_LABELS}")

    # Train Random Forest
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    print("\n" + classification_report(
        y_test, y_pred,
        target_names=RISK_LABELS,
    ))

    # Feature importances
    print("Feature Importances:")
    for name, imp in zip(FEATURE_NAMES, clf.feature_importances_):
        bar = "█" * int(imp * 50)
        print(f"  {name:25s} {imp:.4f}  {bar}")

    # SHAP explainer
    print("\nComputing SHAP values...")
    explainer = shap.TreeExplainer(clf)

    # Save models
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path = os.path.join(MODEL_DIR, "risk_classifier.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"\n✓ Model saved to {model_path}")

    shap_path = os.path.join(MODEL_DIR, "shap_explainer.pkl")
    with open(shap_path, "wb") as f:
        pickle.dump(explainer, f)
    print(f"✓ SHAP explainer saved to {shap_path}")

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    train()
