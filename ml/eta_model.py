import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

df = pd.read_csv("ml/data.csv")

X = df[["distance_km", "hour", "traffic"]]
y = df["delivery_time"]

model = RandomForestRegressor()
model.fit(X, y)

joblib.dump(model, "ml/model.pkl")