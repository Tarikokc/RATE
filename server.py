from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json, os, sqlite3

app = Flask(__name__)

DATA_FILE = "measures.ndjson"
DB_FILE   = "rate.db"

# ─── CORS ────────────────────────────────────────────
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
            sensor_id   TEXT    DEFAULT NULL   -- ← ID de l'ESP (ex: "esp8266-1")
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
            "INSERT INTO rooms (name, capacity, floor, description) VALUES (?,?,?,?)",
            [
                ("Salle A101", 30, "1er étage",  "Salle de cours principale"),
                ("Salle A102", 20, "1er étage",  "Salle de travaux pratiques"),
                ("Salle B201", 15, "2ème étage", "Salle de réunion"),
                ("Amphithéâtre", 100, "RDC",     "Grand amphithéâtre"),
            ]
        )
    c.commit()
    c.close()

init_db()

# ─── Mesures capteur (existant) ───────────────────────
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

# ─── Salles ───────────────────────────────────────────
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    c = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
    c.close()
    return jsonify(rows)

@app.route("/api/rooms", methods=["POST"])
def create_room():
    d = request.get_json(force=True)
    c = db()
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
    now = datetime.utcnow().isoformat()
    soon = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    c = db()
    rooms = [dict(r) for r in c.execute("SELECT * FROM rooms").fetchall()]
    result = []
    for room in rooms:
        current = c.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
        """, (room['id'], now, now)).fetchone()
        upcoming = c.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime>? AND start_datetime<=?
            ORDER BY start_datetime LIMIT 1
        """, (room['id'], now, soon)).fetchone()
        last_measure = None
        if room.get('sensor_id'):
            measures = read_measures()
            for m in reversed(measures):
                if m.get('sensor_id') == room['sensor_id']:
                    last_measure = m
                    break
        result.append({
            **room,
            'current_reservation': dict(current) if current else None,
            'upcoming_reservation': dict(upcoming) if upcoming else None,
            'last_measure': last_measure,
            'heating_needed': upcoming is not None and last_measure is not None
        })
    c.close()
    return jsonify(result)

# ─── Réservations ─────────────────────────────────────
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
    c = db()
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
        return jsonify({"error": "Créneau déjà réservé pour cette salle"}), 409
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

@app.route("/")
def index():
    return jsonify({"status": "RATE API running", "version": "2.0"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
