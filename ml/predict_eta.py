import joblib
from datetime import datetime

model = joblib.load("../ml/model.pkl")

def predict_eta(distance):
    hour = datetime.now().hour
    traffic = 4 if 18 <= hour <= 22 else 2

    pred = model.predict([[distance, hour, traffic]])
    return round(pred[0], 2)
