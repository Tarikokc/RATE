import sys
sys.stdout.reconfigure(encoding='utf-8')

import json, os, pickle
from datetime import datetime, timedelta

import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from backend.database import get_db, init_db
from backend.weather import get_weather
from backend.heating_controller import get_next_reservation, get_current_reservation
from backend.time_helper import now_local, to_local

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ─── IA ───────────────────────────────────────────────────────
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

# ─── Constantes chauffage ─────────────────────────────────────
TARGET_TEMP      = 20.0
HEAT_ADVANCE_MIN = 60
DEG_PER_HOUR     = 2.5
TEMP_TOLERANCE   = 0.5

# ─── Init DB ──────────────────────────────────────────────────
with app.app_context():
    init_db()

# ─── Mesures ──────────────────────────────────────────────────
def append_measure(m):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO measures (sensor_id, room_id, temp, hum, co2, motion, timestamp) VALUES (?,?,?,?,?,?,?)",
            (
                m.get("sensor_id"),
                m.get("room_id"),
                m.get("temp"),
                m.get("hum"),
                m.get("co2"),
                1 if m.get("motion") else 0,
                m.get("timestamp", now_local().isoformat() + "Z")
            )
        )

def read_measures(sensor_id=None, room_id=None, limit=None):
    q = "SELECT * FROM measures WHERE 1=1"
    params = []
    if sensor_id:
        q += " AND sensor_id=?"
        params.append(sensor_id)
    if room_id:
        q += " AND room_id=?"
        params.append(room_id)
    q += " ORDER BY timestamp ASC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for r in rows:
        r["motion"] = bool(r["motion"])
    return rows

def get_last_measure_for_room(room_id):
    with get_db() as conn:
        row = conn.execute("SELECT sensor_id FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not row or not row["sensor_id"]:
            return None
        m = conn.execute(
            "SELECT * FROM measures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1",
            (row["sensor_id"],)
        ).fetchone()
    if not m:
        return None
    result = dict(m)
    result["motion"] = bool(result["motion"])
    return result

def get_last_temp_for_room(room_id):
    m = get_last_measure_for_room(room_id)
    return m.get("temp") if m else None

# ─── Route : réception mesures ESP / RPi ──────────────────────
@app.route("/api/measures", methods=["POST"])
def receive_measure():
    data = request.get_json(force=True)
    sensor_id = data.get("sensor_id") or data.get("sensor")
    if not sensor_id:
        return jsonify({"error": "sensor_id manquant"}), 400

    timestamp = now_local().isoformat() + "Z"

    with get_db() as conn:
        row = conn.execute("SELECT id FROM rooms WHERE sensor_id=?", (sensor_id,)).fetchone()
        room_id = row["id"] if row else data.get("room_id")

        conn.execute(
            "INSERT INTO measures (sensor_id, room_id, temp, hum, co2, motion, timestamp) VALUES (?,?,?,?,?,?,?)",
            (sensor_id, room_id, data.get("temp"), data.get("hum"),
             data.get("co2"), 1 if data.get("motion") else 0, timestamp)
        )
        conn.execute(
            "INSERT INTO sensors(sensor_id, last_seen) VALUES(?,?) "
            "ON CONFLICT(sensor_id) DO UPDATE SET last_seen=excluded.last_seen",
            (sensor_id, timestamp)
        )

    return jsonify({"ok": True}), 200

# ─── Route : mesures filtrées ─────────────────────────────────
@app.route("/api/measures", methods=["GET"])
def get_measures_by_sensor():
    return jsonify(read_measures(
        sensor_id=request.args.get("sensor_id"),
        room_id=request.args.get("room_id"),
        limit=request.args.get("limit")
    ))

# ─── Routes : last / all ──────────────────────────────────────
@app.route("/api/last")
def api_last():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM measures ORDER BY timestamp DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"error": "no data"}), 404
    mesure = dict(row)
    mesure["motion"] = bool(mesure["motion"])
    return jsonify({**mesure, **get_weather()})

@app.route("/api/all")
def api_all():
    return jsonify(read_measures())

# ─── Météo ────────────────────────────────────────────────────
@app.route("/api/weather")
def weather():
    return jsonify(get_weather())

# ─── Logique chauffage ────────────────────────────────────────
def heating_decision(current_temp, upcoming_res, current_res):
    now = now_local()

    if current_temp is not None and current_temp > TARGET_TEMP + 5:
        return {"status": "SURCHAUFFE", "label": "Surchauffe ⚠️", "color": "red",
                "detail": f"{current_temp}°C — dépasse le seuil ({TARGET_TEMP + 5}°C)", "action": "HEAT_OFF"}

    if current_res:
        end       = datetime.fromisoformat(current_res["end_datetime"].replace("Z", ""))
        remaining = int((end - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "OCCUPE", "label": "Occupée", "color": "blue",
                    "detail": f"Fin dans {remaining} min", "action": None}
        if current_temp >= TARGET_TEMP - TEMP_TOLERANCE:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}°C / {TARGET_TEMP}°C — fin dans {remaining} min", "action": None}
        return {"status": "EN_CHAUFFE", "label": "En chauffe", "color": "orange",
                "detail": f"{current_temp}°C → {TARGET_TEMP}°C — fin dans {remaining} min", "action": "HEAT_ON"}

    if upcoming_res:
        start         = datetime.fromisoformat(upcoming_res["start_datetime"].replace("Z", ""))
        minutes_until = int((start - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "PRECHAUFFAGE", "label": "Préchauffage", "color": "orange",
                    "detail": f"Résa dans {minutes_until} min", "action": "HEAT_ON"}
        temp_gap = TARGET_TEMP - current_temp
        if temp_gap <= 0:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}°C — prêt avant {start.strftime('%H:%M')}", "action": None}
        minutes_needed = int((temp_gap / DEG_PER_HOUR) * 60)
        if minutes_until <= minutes_needed + 10:
            return {"status": "PRECHAUFFAGE", "label": "Préchauffage", "color": "orange",
                    "detail": f"{current_temp}°C → {TARGET_TEMP}°C — résa dans {minutes_until} min ({minutes_needed} min de chauffe)",
                    "action": "HEAT_ON"}
        wait = minutes_until - minutes_needed - 10
        return {"status": "ATTENTE", "label": f"Chauffe dans {wait} min", "color": "yellow",
                "detail": f"{current_temp}°C — résa dans {minutes_until} min", "action": "WAIT"}

    return {"status": "STANDBY", "label": "Standby", "color": "gray",
            "detail": f"{current_temp if current_temp else '--'}°C — aucune résa", "action": None}

# ─── Routes : rooms ───────────────────────────────────────────
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
    return jsonify(rows)

@app.route("/api/rooms", methods=["POST"])
def create_room():
    d         = request.get_json(force=True)
    sensor_id = d.get("sensor_id") or None
    if not d.get("name"):
        return jsonify({"error": "name est requis"}), 400

    with get_db() as conn:
        if sensor_id:
            if not conn.execute("SELECT 1 FROM sensors WHERE sensor_id=?", (sensor_id,)).fetchone():
                return jsonify({"error": "Capteur introuvable ou jamais détecté"}), 400
            if conn.execute("SELECT 1 FROM rooms WHERE sensor_id=?", (sensor_id,)).fetchone():
                return jsonify({"error": "Capteur déjà associé à une autre salle"}), 409
        cur = conn.execute(
            "INSERT INTO rooms (name, capacity, floor, description, sensor_id) VALUES (?,?,?,?,?)",
            (d["name"], d.get("capacity", 10), d.get("floor", "RDC"), d.get("description", ""), sensor_id)
        )
        room_id = cur.lastrowid

    return jsonify({"id": room_id, **d, "sensor_id": sensor_id}), 201

@app.route("/api/rooms/<int:rid>", methods=["PATCH"])
def update_room(rid):
    d         = request.get_json(force=True)
    sensor_id = d.get("sensor_id") or None

    with get_db() as conn:
        if sensor_id:
            if not conn.execute("SELECT 1 FROM sensors WHERE sensor_id=?", (sensor_id,)).fetchone():
                return jsonify({"error": "Capteur introuvable ou jamais détecté"}), 400
            if conn.execute("SELECT id FROM rooms WHERE sensor_id=? AND id!=?", (sensor_id, rid)).fetchone():
                return jsonify({"error": "Capteur déjà associé à une autre salle"}), 409
        conn.execute("UPDATE rooms SET sensor_id=? WHERE id=?", (sensor_id, rid))

    return jsonify({"ok": True})

@app.route("/api/rooms/<int:rid>", methods=["DELETE"])
def delete_room(rid):
    with get_db() as conn:
        conn.execute("DELETE FROM rooms WHERE id=?", (rid,))
    return "", 204

# ─── Route : statut des salles (dashboard) ───────────────────
@app.route("/api/rooms/status", methods=["GET"])
def rooms_status():
    now  = now_local().isoformat()
    soon = (now_local() + timedelta(hours=1)).isoformat()
    result = []

    with get_db() as conn:
        rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms").fetchall()]
        for room in rooms:
            current  = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
            """, (room["id"], now, now)).fetchone()
            upcoming = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=? AND start_datetime>? AND start_datetime<=?
                ORDER BY start_datetime LIMIT 1
            """, (room["id"], now, soon)).fetchone()
            next_any = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=? AND start_datetime>?
                ORDER BY start_datetime LIMIT 1
            """, (room["id"], now)).fetchone()

            current_res  = dict(current)  if current  else None
            upcoming_res = dict(upcoming) if upcoming else None
            next_any_res = dict(next_any) if next_any else None
            measure      = get_last_measure_for_room(room["id"])
            current_temp = measure.get("temp") if measure else None

            result.append({
                **room,
                "temp":                 measure.get("temp")   if measure else None,
                "hum":                  measure.get("hum")    if measure else None,
                "co2":                  measure.get("co2")    if measure else None,
                "motion":               measure.get("motion") if measure else None,
                "last_measure":         measure,
                "current_temp":         current_temp,
                "target_temp":          TARGET_TEMP,
                "current_reservation":  current_res,
                "upcoming_reservation": upcoming_res,
                "next_reservation":     next_any_res,
                "heating":              heating_decision(current_temp, upcoming_res, current_res)
            })

    return jsonify(result)

# ─── Routes : capteurs ────────────────────────────────────────
@app.route("/api/sensors/available", methods=["GET"])
def available_sensors():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.sensor_id, s.last_seen FROM sensors s
            WHERE s.sensor_id NOT IN (
                SELECT sensor_id FROM rooms WHERE sensor_id IS NOT NULL
            )
            ORDER BY s.last_seen DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/sensors", methods=["GET"])
def get_sensors():
    with get_db() as conn:
        rows = conn.execute("SELECT sensor_id, last_seen FROM sensors ORDER BY last_seen DESC").fetchall()
    return jsonify([dict(r) for r in rows])

# ─── Routes : réservations ────────────────────────────────────
@app.route("/api/reservations", methods=["GET"])
def get_reservations():
    date    = request.args.get("date")
    room_id = request.args.get("room_id")
    q = """
        SELECT r.*, rm.name AS room_name, rm.capacity, rm.floor
        FROM reservations r
        JOIN rooms rm ON r.room_id = rm.id
        WHERE 1=1
    """
    params = []
    if date:
        q += " AND DATE(r.start_datetime) = ?"
        params.append(date)
    if room_id:
        q += " AND r.room_id = ?"
        params.append(int(room_id))
    q += " ORDER BY r.start_datetime"
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    return jsonify(rows)

@app.route("/api/reservations", methods=["POST"])
def create_reservation():
    d = request.get_json(force=True)
    with get_db() as conn:
        conflict = conn.execute("""
            SELECT id FROM reservations
            WHERE room_id=? AND NOT (end_datetime<=? OR start_datetime>=?)
        """, (d["room_id"], d["start_datetime"], d["end_datetime"])).fetchone()
        if conflict:
            return jsonify({"error": "Créneau déjà réservé pour cette salle"}), 409
        cur = conn.execute(
            "INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count) VALUES (?,?,?,?,?,?)",
            (d["room_id"], d["user_name"], d["title"], d["start_datetime"], d["end_datetime"], d.get("people_count", 1))
        )
        new_id = cur.lastrowid
    return jsonify({**d, "id": new_id}), 201

@app.route("/api/reservations/<int:rid>", methods=["DELETE"])
def delete_reservation(rid):
    with get_db() as conn:
        conn.execute("DELETE FROM reservations WHERE id=?", (rid,))
    return "", 204

# ─── Route : décision chauffage (toutes salles) ───────────────
@app.route("/api/heating/decision")
def heating_decision_api():
    with get_db() as conn:
        rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms").fetchall()]
    return jsonify([{
        "room":         room["name"],
        "current_temp": get_last_temp_for_room(room["id"]),
        "decision":     heating_decision(
                            get_last_temp_for_room(room["id"]),
                            get_next_reservation(room["id"]),
                            get_current_reservation(room["id"]))
    } for room in rooms])

# ─── Route : prédiction IA ────────────────────────────────────
@app.route("/api/predict/<int:room_id>")
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

    w = get_weather()
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

# ─── Serve Angular ────────────────────────────────────────────
DIST = os.path.join(os.path.dirname(__file__), "clientApp", "dist", "client-app", "browser")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_angular(path):
    full = os.path.join(DIST, path)
    if path and os.path.exists(full):
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)