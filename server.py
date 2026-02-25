# from flask import Flask, request, jsonify
# from datetime import datetime, timedelta
# import json, os, sqlite3

# app = Flask(__name__)

# DATA_FILE = "measures.ndjson"
# DB_FILE   = "rate.db"

# # ─── CORS ────────────────────────────────────────────
# @app.after_request
# def cors(r):
#     r.headers["Access-Control-Allow-Origin"]  = "*"
#     r.headers["Access-Control-Allow-Headers"] = "Content-Type"
#     r.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
#     return r

# @app.before_request
# def preflight():
#     if request.method == "OPTIONS":
#         return jsonify({}), 200

# # ─── SQLite ───────────────────────────────────────────
# def db():
#     conn = sqlite3.connect(DB_FILE)
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     c = db()
#     c.executescript("""
#         CREATE TABLE IF NOT EXISTS rooms (
#             id          INTEGER PRIMARY KEY AUTOINCREMENT,
#             name        TEXT    NOT NULL,
#             capacity    INTEGER DEFAULT 10,
#             floor       TEXT    DEFAULT 'RDC',
#             description TEXT    DEFAULT '',
#             sensor_id   TEXT    DEFAULT NULL   -- ← ID de l'ESP (ex: "esp8266-1")
#         );
#         CREATE TABLE IF NOT EXISTS reservations (
#             id             INTEGER PRIMARY KEY AUTOINCREMENT,
#             room_id        INTEGER NOT NULL,
#             user_name      TEXT    NOT NULL,
#             title          TEXT    NOT NULL,
#             start_datetime TEXT    NOT NULL,
#             end_datetime   TEXT    NOT NULL,
#             people_count   INTEGER DEFAULT 1,
#             created_at     TEXT    DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
#         );
#     """)
#     if not c.execute("SELECT 1 FROM rooms LIMIT 1").fetchone():
#         c.executemany(
#             "INSERT INTO rooms (name, capacity, floor, description) VALUES (?,?,?,?)",
#             [
#                 ("Salle A101", 30, "1er étage",  "Salle de cours principale"),
#                 ("Salle A102", 20, "1er étage",  "Salle de travaux pratiques"),
#                 ("Salle B201", 15, "2ème étage", "Salle de réunion"),
#                 ("Amphithéâtre", 100, "RDC",     "Grand amphithéâtre"),
#             ]
#         )
#     c.commit()
#     c.close()

# init_db()

# # ─── Mesures capteur (existant) ───────────────────────
# def append_measure(m):
#     with open(DATA_FILE, "a", encoding="utf-8") as f:
#         f.write(json.dumps(m) + "\n")

# def read_measures():
#     if not os.path.exists(DATA_FILE):
#         return []
#     out = []
#     with open(DATA_FILE, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if line:
#                 try:   out.append(json.loads(line))
#                 except: pass
#     return out

# @app.route("/measure", methods=["POST"])
# def measure():
#     data = request.get_json(force=True)
#     data["timestamp"] = datetime.utcnow().isoformat() + "Z"
#     append_measure(data)
#     return "OK", 200

# @app.route("/api/last")
# def api_last():
#     m = read_measures()
#     return jsonify(m[-1]) if m else (jsonify({"error": "no data"}), 404)

# @app.route("/api/all")
# def api_all():
#     return jsonify(read_measures())

# # ─── Salles ───────────────────────────────────────────
# @app.route("/api/rooms", methods=["GET"])
# def get_rooms():
#     c = db()
#     rows = [dict(r) for r in c.execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
#     c.close()
#     return jsonify(rows)

# @app.route("/api/rooms", methods=["POST"])
# def create_room():
#     d = request.get_json(force=True)
#     c = db()
#     cur = c.execute(
#         "INSERT INTO rooms (name, capacity, floor, description) VALUES (?,?,?,?)",
#         (d["name"], d.get("capacity", 10), d.get("floor", "RDC"), d.get("description", ""))
#     )
#     c.commit()
#     room_id = cur.lastrowid
#     c.close()
#     return jsonify({**d, "id": room_id}), 201

# @app.route("/api/rooms/<int:rid>", methods=["DELETE"])
# def delete_room(rid):
#     c = db()
#     c.execute("DELETE FROM rooms WHERE id=?", (rid,))
#     c.commit()
#     c.close()
#     return "", 204

# @app.route("/api/rooms/status")
# def rooms_status():
#     now = datetime.utcnow().isoformat()
#     soon = (datetime.utcnow() + timedelta(hours=1)).isoformat()
#     c = db()
#     rooms = [dict(r) for r in c.execute("SELECT * FROM rooms").fetchall()]
#     result = []
#     for room in rooms:
#         current = c.execute("""
#             SELECT * FROM reservations
#             WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
#         """, (room['id'], now, now)).fetchone()
#         upcoming = c.execute("""
#             SELECT * FROM reservations
#             WHERE room_id=? AND start_datetime>? AND start_datetime<=?
#             ORDER BY start_datetime LIMIT 1
#         """, (room['id'], now, soon)).fetchone()
#         last_measure = None
#         if room.get('sensor_id'):
#             measures = read_measures()
#             for m in reversed(measures):
#                 if m.get('sensor_id') == room['sensor_id']:
#                     last_measure = m
#                     break
#         result.append({
#             **room,
#             'current_reservation': dict(current) if current else None,
#             'upcoming_reservation': dict(upcoming) if upcoming else None,
#             'last_measure': last_measure,
#             'heating_needed': upcoming is not None and last_measure is not None
#         })
#     c.close()
#     return jsonify(result)

# # ─── Réservations ─────────────────────────────────────
# @app.route("/api/reservations", methods=["GET"])
# def get_reservations():
#     date    = request.args.get("date")
#     room_id = request.args.get("room_id")
#     q = """
#         SELECT r.*, rm.name AS room_name, rm.capacity, rm.floor
#         FROM reservations r
#         JOIN rooms rm ON r.room_id = rm.id
#         WHERE 1=1
#     """
#     params = []
#     if date:
#         q += " AND DATE(r.start_datetime) = ?"
#         params.append(date)
#     if room_id:
#         q += " AND r.room_id = ?"
#         params.append(int(room_id))
#     q += " ORDER BY r.start_datetime"
#     c = db()
#     rows = [dict(r) for r in c.execute(q, params).fetchall()]
#     c.close()
#     return jsonify(rows)

# @app.route("/api/reservations", methods=["POST"])
# def create_reservation():
#     d = request.get_json(force=True)
#     c = db()
#     conflict = c.execute("""
#         SELECT id FROM reservations
#         WHERE room_id = ?
#           AND NOT (end_datetime <= ? OR start_datetime >= ?)
#     """, (d["room_id"], d["start_datetime"], d["end_datetime"])).fetchone()
#     if conflict:
#         c.close()
#         return jsonify({"error": "Créneau déjà réservé pour cette salle"}), 409
#     cur = c.execute(
#         "INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count) VALUES (?,?,?,?,?,?)",
#         (d["room_id"], d["user_name"], d["title"], d["start_datetime"], d["end_datetime"], d.get("people_count", 1))
#     )
#     c.commit()
#     new_id = cur.lastrowid
#     c.close()
#     return jsonify({**d, "id": new_id}), 201

# @app.route("/api/reservations/<int:rid>", methods=["DELETE"])
# def delete_reservation(rid):
#     c = db()
#     c.execute("DELETE FROM reservations WHERE id=?", (rid,))
#     c.commit()
#     c.close()
#     return "", 204

# @app.route("/")
# def index():
#     return jsonify({"status": "RATE API running", "version": "2.0"})

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import json, os, sqlite3

app = Flask(__name__)

DATA_FILE = "measures.ndjson"
DB_FILE   = "rate.db"

# ─── Météo ────────────────────────────────────────────
from weather import get_weather

# ─── IA ───────────────────────────────────────────────
try:
    import tensorflow as tf
    import pickle
    import numpy as np

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

# ─── Constantes chauffage ─────────────────────────────
TARGET_TEMP      = 20.0
HEAT_ADVANCE_MIN = 60
DEG_PER_HOUR     = 2.5
TEMP_TOLERANCE   = 0.5

# ─── CORS ─────────────────────────────────────────────
@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    return r

@app.before_request
def preflight():
    if request.method == "OPTIONS":
        return jsonify({}), 200

# ─── SQLite ───────────────────────────────────────────
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            capacity    INTEGER DEFAULT 10,
            floor       TEXT    DEFAULT 'RDC',
            description TEXT    DEFAULT '',
            sensor_id   TEXT    DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS reservations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id        INTEGER NOT NULL,
            user_name      TEXT    NOT NULL,
            title          TEXT    NOT NULL,
            start_datetime TEXT    NOT NULL,
            end_datetime   TEXT    NOT NULL,
            people_count   INTEGER DEFAULT 1,
            created_at     TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        );
    """)
    if not c.execute("SELECT 1 FROM rooms LIMIT 1").fetchone():
        c.executemany(
            "INSERT INTO rooms (name, capacity, floor, description, sensor_id) VALUES (?,?,?,?,?)",
            [
                ("Salle A101",    30,  "1er etage",  "Salle de cours principale",  "rpi5-room-1"),
                ("Salle A102",    20,  "1er etage",  "Salle de travaux pratiques", "rpi5-room-2"),
                ("Salle B201",    15,  "2eme etage", "Salle de reunion",           "rpi5-room-3"),
                ("Amphi",        100,  "RDC",        "Grand amphitheatre",         "rpi5-room-4"),
            ]
        )
    c.commit()
    c.close()

init_db()

# ─── Mesures capteur ──────────────────────────────────
def append_measure(m):
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(m) + "\n")

def read_measures():
    if not os.path.exists(DATA_FILE):
        return []
    out = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:   out.append(json.loads(line))
                except: pass
    return out

def get_last_temp_for_room(room_id):
    measures = read_measures()
    for m in reversed(measures):
        if m.get("room_id") == room_id or m.get("sensor_id") == f"rpi5-room-{room_id}":
            return m.get("temp")
    return None

@app.route("/measure", methods=["POST"])
def measure():
    data = request.get_json(force=True)
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    append_measure(data)
    return "OK", 200

@app.route("/api/last")
def api_last():
    m = read_measures()
    return jsonify(m[-1]) if m else (jsonify({"error": "no data"}), 404)

@app.route("/api/all")
def api_all():
    return jsonify(read_measures())

# ─── Météo ────────────────────────────────────────────
@app.route("/api/weather")
def weather():
    return jsonify(get_weather())

# ─── Logique chauffage ────────────────────────────────
def heating_decision(current_temp, upcoming_res, current_res):
    now = datetime.utcnow()

    if current_res:
        end       = datetime.fromisoformat(current_res["end_datetime"].replace("Z", ""))
        remaining = int((end - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "OCCUPE",         "label": "Occupee",          "color": "blue",
                    "detail": f"Fin dans {remaining} min", "action": None}
        if current_temp >= TARGET_TEMP - TEMP_TOLERANCE:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte",   "color": "green",
                    "detail": f"{current_temp}C / {TARGET_TEMP}C - Fin dans {remaining} min", "action": None}
        return {"status": "EN_CHAUFFE",         "label": "En chauffe",       "color": "orange",
                "detail": f"{current_temp}C -> {TARGET_TEMP}C - Fin dans {remaining} min", "action": "HEAT_ON"}

    if upcoming_res:
        start         = datetime.fromisoformat(upcoming_res["start_datetime"].replace("Z", ""))
        minutes_until = int((start - now).total_seconds() / 60)

        if current_temp is None:
            return {"status": "PRECHAUFFAGE", "label": "Prechauffage", "color": "orange",
                    "detail": f"Resa dans {minutes_until} min", "action": "HEAT_ON"}

        temp_gap = TARGET_TEMP - current_temp
        if temp_gap <= 0:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}C pret avant {start.strftime('%H:%M')}", "action": None}

        minutes_needed = int((temp_gap / DEG_PER_HOUR) * 60)
        if minutes_until <= minutes_needed + 10:
            return {"status": "PRECHAUFFAGE", "label": "Prechauffage", "color": "orange",
                    "detail": f"{current_temp}C -> {TARGET_TEMP}C - Resa dans {minutes_until} min ({minutes_needed} min de chauffe)",
                    "action": "HEAT_ON"}

        wait = minutes_until - minutes_needed - 10
        return {"status": "ATTENTE", "label": f"Chauffe dans {wait} min", "color": "yellow",
                "detail": f"{current_temp}C - Resa dans {minutes_until} min", "action": "WAIT"}

    return {"status": "STANDBY", "label": "Standby", "color": "gray",
            "detail": f"{current_temp if current_temp else '--'}C - Aucune resa", "action": None}

# ─── Salles ───────────────────────────────────────────
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    c    = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
    c.close()
    return jsonify(rows)

@app.route("/api/rooms", methods=["POST"])
def create_room():
    d   = request.get_json(force=True)
    c   = db()
    cur = c.execute(
        "INSERT INTO rooms (name, capacity, floor, description) VALUES (?,?,?,?)",
        (d["name"], d.get("capacity", 10), d.get("floor", "RDC"), d.get("description", ""))
    )
    c.commit()
    room_id = cur.lastrowid
    c.close()
    return jsonify({**d, "id": room_id}), 201

@app.route("/api/rooms/<int:rid>", methods=["DELETE"])
def delete_room(rid):
    c = db()
    c.execute("DELETE FROM rooms WHERE id=?", (rid,))
    c.commit()
    c.close()
    return "", 204

@app.route("/api/rooms/status")
def rooms_status():
    now  = datetime.utcnow().isoformat()
    soon = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    c    = db()
    rooms  = [dict(r) for r in c.execute("SELECT * FROM rooms").fetchall()]
    result = []

    for room in rooms:
        current = c.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
        """, (room["id"], now, now)).fetchone()

        upcoming = c.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime>? AND start_datetime<=?
            ORDER BY start_datetime LIMIT 1
        """, (room["id"], now, soon)).fetchone()

        next_any = c.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime>?
            ORDER BY start_datetime LIMIT 1
        """, (room["id"], now)).fetchone()

        current_res  = dict(current)  if current  else None
        upcoming_res = dict(upcoming) if upcoming else None
        next_any_res = dict(next_any) if next_any else None
        current_temp = get_last_temp_for_room(room["id"])
        decision     = heating_decision(current_temp, upcoming_res, current_res)

        result.append({
            **room,
            "current_temp":         current_temp,
            "target_temp":          TARGET_TEMP,
            "current_reservation":  current_res,
            "upcoming_reservation": upcoming_res,
            "next_reservation":     next_any_res,
            "heating":              decision
        })

    c.close()
    return jsonify(result)

# ─── Reservations ─────────────────────────────────────
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
    c    = db()
    rows = [dict(r) for r in c.execute(q, params).fetchall()]
    c.close()
    return jsonify(rows)

@app.route("/api/reservations", methods=["POST"])
def create_reservation():
    d = request.get_json(force=True)
    c = db()
    conflict = c.execute("""
        SELECT id FROM reservations
        WHERE room_id = ?
          AND NOT (end_datetime <= ? OR start_datetime >= ?)
    """, (d["room_id"], d["start_datetime"], d["end_datetime"])).fetchone()
    if conflict:
        c.close()
        return jsonify({"error": "Creneau deja reserve pour cette salle"}), 409
    cur = c.execute(
        "INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count) VALUES (?,?,?,?,?,?)",
        (d["room_id"], d["user_name"], d["title"], d["start_datetime"], d["end_datetime"], d.get("people_count", 1))
    )
    c.commit()
    new_id = cur.lastrowid
    c.close()
    return jsonify({**d, "id": new_id}), 201

@app.route("/api/reservations/<int:rid>", methods=["DELETE"])
def delete_reservation(rid):
    c = db()
    c.execute("DELETE FROM reservations WHERE id=?", (rid,))
    c.commit()
    c.close()
    return "", 204

# ─── Prediction IA ────────────────────────────────────
@app.route("/api/predict/<int:room_id>")
def predict(room_id):
    if not AI_READY:
        return jsonify({"error": "Modele IA non charge"}), 503

    measures = [m for m in read_measures()
                if m.get("room_id") == room_id][-12:]

    if len(measures) < 12:
        return jsonify({"error": "Pas assez de donnees (min 12)"}), 400

    w    = get_weather()
    rows = []
    for m in measures:
        ts = datetime.fromisoformat(m["timestamp"].replace("Z", ""))
        rows.append([
            m.get("temp",             17),
            m.get("hum",              50),
            m.get("co2",             600),
            int(m.get("motion",    False)),
            ts.hour,
            ts.weekday(),
            1 if ts.weekday() >= 5 else 0,
            m.get("people_count",      0),
            m.get("room_capacity",    30),
            m.get("occupancy_rate",    0),
            m.get("minutes_to_start", 999),
            m.get("is_occupied",       0),
            m.get("res_duration_min",  0),
            w["outdoor_temp"],
            w["outdoor_hum"],
            w["wind_speed"]
        ])

    X   = np.array([scaler_X.transform(rows)], dtype=np.float32)
    inp = interpreter.get_input_details()
    out = interpreter.get_output_details()
    interpreter.set_tensor(inp[0]["index"], X)
    interpreter.invoke()
    pred = scaler_y.inverse_transform(
        interpreter.get_tensor(out[0]["index"])
    )[0][0]

    return jsonify({
        "room_id":        room_id,
        "predicted_temp": round(float(pred), 2),
        "outdoor_temp":   w["outdoor_temp"],
        "horizon":        "5 minutes"
    })

# ─── Serve Angular ────────────────────────────────────
DIST = os.path.join(os.path.dirname(__file__), "clientApp", "dist", "client-app", "browser")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_angular(path):
    full = os.path.join(DIST, path)
    if path and os.path.exists(full):
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
