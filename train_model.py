import json, pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

# ── Charger les données ───────────────────────────────
measures = []
with open("measures.ndjson") as f:
    for line in f:
        line = line.strip()
        if line:
            measures.append(json.loads(line))

df = pd.DataFrame(measures)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["room_id", "timestamp"]).reset_index(drop=True)

FEATURES = [
    "temp", "hum", "co2", "motion",
    "hour", "weekday", "is_weekend",
    "people_count", "room_capacity", "occupancy_rate",
    "minutes_to_start", "is_occupied", "res_duration_min",
    "outdoor_temp", "outdoor_hum", "wind_speed"
]
TARGET  = "temp"
SEQ_LEN = 12   # 12 mesures × 5min = 1h d'historique

# ── Normaliser ────────────────────────────────────────
scaler_X = MinMaxScaler()
scaler_y = MinMaxScaler()

X_scaled = scaler_X.fit_transform(df[FEATURES])
y_scaled = scaler_y.fit_transform(df[[TARGET]])

# ── Séquences ─────────────────────────────────────────
X_seq, y_seq = [], []
for i in range(SEQ_LEN, len(X_scaled)):
    X_seq.append(X_scaled[i - SEQ_LEN:i])
    y_seq.append(y_scaled[i])

X_seq = np.array(X_seq)
y_seq = np.array(y_seq)
print(f"Dataset : {X_seq.shape[0]} séquences — {len(FEATURES)} features")

# ── Modèle LSTM ───────────────────────────────────────
model = tf.keras.Sequential([
    tf.keras.layers.LSTM(64, return_sequences=True,
                         input_shape=(SEQ_LEN, len(FEATURES))),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.LSTM(32),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(1)
])
model.compile(optimizer="adam", loss="mse", metrics=["mae"])
model.summary()

# ── Entraînement ──────────────────────────────────────
history = model.fit(
    X_seq, y_seq,
    epochs=20,
    batch_size=32,
    validation_split=0.2,
    verbose=1
)

print(f"\n✅ MAE finale : {history.history['mae'][-1]:.4f}°C")

# ── Export TFLite ─────────────────────────────────────
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS,
    tf.lite.OpsSet.SELECT_TF_OPS
]
converter._experimental_lower_tensor_list_ops = False
tflite_model = converter.convert()
with open("rate_model.tflite", "wb") as f:
    f.write(tflite_model)

# ── Sauvegarder les scalers ───────────────────────────
with open("scaler_X.pkl", "wb") as f: pickle.dump(scaler_X, f)
with open("scaler_y.pkl", "wb") as f: pickle.dump(scaler_y, f)
with open("features.json", "w") as f: json.dump(FEATURES, f)

print("✅ rate_model.tflite + scaler_X.pkl + scaler_y.pkl + features.json")
