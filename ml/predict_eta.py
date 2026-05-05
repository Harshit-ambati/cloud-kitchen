import joblib
import pandas as pd
from datetime import datetime
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().with_name("model.pkl")
model = joblib.load(MODEL_PATH)

def predict_eta(distance):
    hour = datetime.now().hour
    traffic = 4 if 18 <= hour <= 22 else 2

    features = pd.DataFrame(
        [[distance, hour, traffic]],
        columns=["distance_km", "hour", "traffic"],
    )
    pred = model.predict(features)
    return round(pred[0], 2)
