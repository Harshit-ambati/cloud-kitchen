"""
ML Training Pipeline - Generates data and trains the ETA prediction model
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("🚀 Starting ML Pipeline...")

# Step 1: Generate Training Data
print("\n📊 Step 1: Generating training data...")
from ml.training.generate_data import df as generated_df
print(f"✓ Generated {len(generated_df)} training samples")

# Step 2: Train the Model
print("\n🤖 Step 2: Training ETA prediction model...")
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

df = pd.read_csv("ml/data.csv")
X = df[["distance_km", "hour", "traffic"]]
y = df["delivery_time"]

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

# Save the model
model_path = "ml/model.pkl"
joblib.dump(model, model_path)
print(f"✓ Model trained and saved to {model_path}")

# Step 3: Test the Model
print("\n✅ Step 3: Testing model...")
from ml.predict_eta import predict_eta
test_distance = 5.0
eta = predict_eta(test_distance)
print(f"✓ Test prediction: distance={test_distance}km, ETA={eta} minutes")

print("\n✨ ML Pipeline completed successfully!")
