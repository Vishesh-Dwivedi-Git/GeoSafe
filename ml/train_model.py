import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib

# Load dataset
df = pd.read_csv("ml/dataset.csv")

# Split features and label
X = df.drop("label", axis=1)
y = df["label"]

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Improved RandomForest
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42
)

model.fit(X_train, y_train)

# Accuracy
accuracy = model.score(X_test, y_test)
print(f"Model Accuracy: {accuracy:.4f}")

# Feature importance
feature_names = X.columns
importances = model.feature_importances_

print("\nFeature Importance:")
for name, imp in zip(feature_names, importances):
    print(f"{name}: {imp:.3f}")

# Save model
joblib.dump(model, "ml/model.pkl")
joblib.dump(le, "ml/label_encoder.pkl")

print("\nModel saved successfully!")