import json, os, pickle
import numpy as np
from flask import Blueprint, jsonify
from app.database import get_db
from app.measures_service import read_measures
from app.weather import get_weather
from datetime import datetime

bp = Blueprint("predict", __name__)

# ─── Chargement IA au démarrage ───────────────────────────────
try:
    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path="rate_model.tflite")
    interpreter.allocate_tensors()
    with open("scaler_X.pkl", "rb") as f: scaler_X = pickle.load(f)
    with open("scaler_y.pkl", "rb") as f: scaler_y = pickle.load(f)
    with open("features.json", "r") as f: FEATURES = json.load(f)
    AI_READY = True
    print("[IA] Modele charge")
except Exception as e:
    AI_READY = False
    print(f"[IA] Non disponible : {e}")

@bp.route("/api/predict/<int:room_id>")
def predict(room_id):
    if not AI_READY:
        return jsonify({"error": "Modele IA non chargé"}), 503

    with get_db() as conn:
        row = conn.execute("SELECT sensor_id FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not row or not row["sensor_id"]:
        return jsonify({"error": "Salle sans capteur"}), 400

    measures = read_measures(sensor_id=row["sensor_id"], limit=12)
    if len(measures) < 12:
        return jsonify({"error": "Pas assez de données (min 12)"}), 400

    w    = get_weather()
    rows = []
    for m in measures:
        ts = datetime.fromisoformat(m["timestamp"].replace("Z", ""))
        rows.append([
            m.get("temp", 17), m.get("hum", 50), m.get("co2", 600),
            int(m.get("motion", False)), ts.hour, ts.weekday(),
            1 if ts.weekday() >= 5 else 0,
            m.get("people_count", 0), m.get("room_capacity", 30),
            m.get("occupancy_rate", 0), m.get("minutes_to_start", 999),
            m.get("is_occupied", 0), m.get("res_duration_min", 0),
            w["outdoor_temp"], w["outdoor_hum"], w["wind_speed"]
        ])

    X   = np.array([scaler_X.transform(rows)], dtype=np.float32)
    inp = interpreter.get_input_details()
    out = interpreter.get_output_details()
    interpreter.set_tensor(inp[0]["index"], X)
    interpreter.invoke()
    pred = scaler_y.inverse_transform(interpreter.get_tensor(out[0]["index"]))[0][0]

    return jsonify({"room_id": room_id, "predicted_temp": round(float(pred), 2),
                    "outdoor_temp": w["outdoor_temp"], "horizon": "5 minutes"})