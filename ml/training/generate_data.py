import pandas as pd
import numpy as np

n = 5000

df = pd.DataFrame({
    "distance_km": np.random.uniform(1, 10, n),
    "hour": np.random.randint(0, 24, n),
    "traffic": np.random.randint(1, 5, n)
})

df["delivery_time"] = (
    df["distance_km"] * 5 +
    df["traffic"] * 3 +
    np.where((df["hour"] >= 18) & (df["hour"] <= 22), 10, 0)
)

df.to_csv("ml/data.csv", index=False)