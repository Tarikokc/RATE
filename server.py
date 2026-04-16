import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, request, jsonify, send_from_directory, g
from datetime import datetime, timedelta
import json, os, sqlite3
from weather import get_weather
from heating_controller import get_next_reservation, get_current_reservation

app = Flask(__name__)

DB_FILE = "rate.db"

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

# ─── SQLite (connexion par contexte Flask) ────────────
def db():
    """Retourne la connexion SQLite du contexte Flask (une seule par requête)."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
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
        CREATE TABLE IF NOT EXISTS measures (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT    NOT NULL,
            room_id    INTEGER,
            sensor_id  TEXT,
            temp       REAL,
            hum        REAL,
            co2        REAL,
            motion     INTEGER DEFAULT 0,
            extra      TEXT    DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_measures_room_ts
            ON measures (room_id, timestamp DESC);
    """)
    if not conn.execute("SELECT 1 FROM rooms LIMIT 1").fetchone():
        conn.executemany(
            "INSERT INTO rooms (name, capacity, floor, description, sensor_id) VALUES (?,?,?,?,?)",
            [
                ("Salle A101",    30,  "1er etage",  "Salle de cours principale",  "rpi5-room-1"),
                ("Salle A102",    20,  "1er etage",  "Salle de travaux pratiques", "rpi5-room-2"),
                ("Salle B201",    15,  "2eme etage", "Salle de reunion",           "rpi5-room-3"),
                ("Amphi",        100,  "RDC",        "Grand amphitheatre",         "rpi5-room-4"),
            ]
        )
    conn.commit()
    conn.close()

init_db()

# ─── Helpers migration NDJSON → SQLite ───────────────
def _row_to_dict(row):
    """Convertit une Row SQLite en dict, en dépliant le champ extra."""
    d = dict(row)
    try:
        extra = json.loads(d.pop('extra') or '{}')
        d.update(extra)
    except Exception:
        pass
    return d

def append_measure(m: dict):
    """Insère une mesure dans SQLite."""
    extra_keys = set(m.keys()) - {'timestamp', 'room_id', 'sensor_id', 'temp', 'hum', 'co2', 'motion'}
    extra = {k: m[k] for k in extra_keys}
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO measures (timestamp, room_id, sensor_id, temp, hum, co2, motion, extra)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (
            m.get('timestamp'),
            m.get('room_id'),
            m.get('sensor_id'),
            m.get('temp'),
            m.get('hum'),
            m.get('co2'),
            int(bool(m.get('motion', False))),
            json.dumps(extra),
        )
    )
    conn.commit()
    conn.close()

def read_measures(limit: int = None, room_id: int = None):
    """Lit les mesures depuis SQLite avec support LIMIT et filtre room_id."""
    q = "SELECT * FROM measures"
    params = []
    if room_id is not None:
        q += " WHERE room_id = ?"
        params.append(room_id)
    q += " ORDER BY timestamp ASC"
    if limit:
        q += " LIMIT ?"
        params.append(limit)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = [_row_to_dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows

def get_last_measure(room_id: int = None):
    """Récupère la dernière mesure (optionnellement filtrée par room_id)."""
    q = "SELECT * FROM measures"
    params = []
    if room_id is not None:
        q += " WHERE room_id = ?"
        params.append(room_id)
    q += " ORDER BY timestamp DESC LIMIT 1"
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(q, params).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None

def get_last_temp_for_room(room_id):
    row = get_last_measure(room_id)
    if row:
        return row.get('temp')
    # fallback mono-capteur
    row = get_last_measure()
    return row.get('temp') if row else None

@app.route("/measure", methods=["POST"])
def measure():
    data = request.get_json(force=True)
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    append_measure(data)
    return "OK", 200

@app.route("/api/last")
def api_last():
    mesure = get_last_measure()
    if not mesure:
        return jsonify({"error": "no data"}), 404
    meteo   = get_weather()
    payload = {**mesure, **meteo}
    return jsonify(payload)

@app.route("/api/all")
def api_all():
    limit  = request.args.get('limit',  type=int)
    offset = request.args.get('offset', type=int, default=0)
    q      = "SELECT * FROM measures ORDER BY timestamp ASC"
    params = []
    if limit:
        q += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = [_row_to_dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)

# ─── Météo ────────────────────────────────────────────
@app.route("/api/weather")
def weather():
    return jsonify(get_weather())

# ─── Logique chauffage ────────────────────────────────
def heating_decision(current_temp, upcoming_res, current_res):
    now = datetime.utcnow()

    if current_temp is not None and current_temp > TARGET_TEMP + 5:
        return {"status": "SURCHAUFFE", "label": "Surchauffe ⚠️", "color": "red",
                "detail": f"{current_temp}°C — dépasse le seuil de surchauffe ({TARGET_TEMP + 5}°C)",
                "action": "HEAT_OFF"}

    if current_res:
        end       = datetime.fromisoformat(current_res["end_datetime"].replace("Z", ""))
        remaining = int((end - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "OCCUPE",         "label": "Occupee",        "color": "blue",
                    "detail": f"Fin dans {remaining} min", "action": None}
        if current_temp >= TARGET_TEMP - TEMP_TOLERANCE:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}°C / {TARGET_TEMP}°C — fin dans {remaining} min", "action": None}
        return {"status": "EN_CHAUFFE",         "label": "En chauffe",     "color": "orange",
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

# ─── Salles ───────────────────────────────────────────
@app.route("/api/rooms", methods=["GET"], strict_slashes=False)
def get_rooms():
    rows = [dict(r) for r in db().execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
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
    return jsonify({**d, "id": cur.lastrowid}), 201

@app.route("/api/rooms/<int:rid>", methods=["DELETE"])
def delete_room(rid):
    c = db()
    c.execute("DELETE FROM rooms WHERE id=?", (rid,))
    c.commit()
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
    rows = [dict(r) for r in db().execute(q, params).fetchall()]
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
        return jsonify({"error": "Creneau deja reserve pour cette salle"}), 409
    cur = c.execute(
        "INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count) VALUES (?,?,?,?,?,?)",
        (d["room_id"], d["user_name"], d["title"], d["start_datetime"], d["end_datetime"], d.get("people_count", 1))
    )
    c.commit()
    return jsonify({**d, "id": cur.lastrowid}), 201

@app.route("/api/reservations/<int:rid>", methods=["DELETE"])
def delete_reservation(rid):
    c = db()
    c.execute("DELETE FROM reservations WHERE id=?", (rid,))
    c.commit()
    return "", 204

# ─── Prediction IA ────────────────────────────────────
@app.route("/api/predict/<int:room_id>")
def predict(room_id):
    if not AI_READY:
        return jsonify({"error": "Modele IA non charge"}), 503

    measures = read_measures(limit=12, room_id=room_id)
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

@app.route("/api/heating/decision")
def heating_decision_api():
    rooms  = [dict(r) for r in db().execute("SELECT * FROM rooms").fetchall()]
    result = []
    for room in rooms:
        current_temp = get_last_temp_for_room(room["id"])
        result.append({
            "room":         room["name"],
            "current_temp": current_temp,
            "decision":     heating_decision(
                                current_temp,
                                get_next_reservation(room["id"]),
                                get_current_reservation(room["id"]))
        })
    return jsonify(result)

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
