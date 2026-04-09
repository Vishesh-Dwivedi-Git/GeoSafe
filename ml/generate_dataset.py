import random
import pandas as pd

def generate_sample():
    distance_to_water = random.uniform(0, 500)
    water_overlap = random.uniform(0, 1)
    inside_forest = random.choice([0, 1])
    inside_esz = random.choice([0, 1])
    flood_risk = random.uniform(0, 1)
    govt_land_overlap = random.uniform(0, 1)

    score = 0

    # weighted scoring (more realistic than strict rules)
    if inside_esz:
        score += 4
    if inside_forest:
        score += 3
    if water_overlap > 0.3:
        score += 2
    if distance_to_water < 50:
        score += 2
    if flood_risk > 0.6:
        score += 2
    if govt_land_overlap > 0.5:
        score += 1

    # add randomness (CRITICAL)
    score += random.uniform(-1.5, 1.5)

    # label assignment
    if score >= 5:
        label = "HIGH"
    elif score >= 3:
        label = "MEDIUM"
    else:
        label = "LOW"

    return [
        distance_to_water,
        water_overlap,
        inside_forest,
        inside_esz,
        flood_risk,
        govt_land_overlap,
        label
    ]

# generate larger dataset
data = [generate_sample() for _ in range(10000)]

columns = [
    "distance_to_water",
    "water_overlap",
    "inside_forest",
    "inside_esz",
    "flood_risk",
    "govt_land_overlap",
    "label"
]

df = pd.DataFrame(data, columns=columns)
df.to_csv("ml/dataset.csv", index=False)

print("Dataset generated with noise and 10k samples!")