from flask import Blueprint, request, jsonify
from app.database import get_db
from app.measures_service import append_measure, read_measures
from app.weather import get_weather
from app.time_helper import now_local

bp = Blueprint("measures", __name__)

@bp.route("/api/measures", methods=["POST"])
def receive_measure():
    data      = request.get_json(force=True)
    sensor_id = data.get("sensor_id") or data.get("sensor")
    if not sensor_id:
        return jsonify({"error": "sensor_id manquant"}), 400

    timestamp = now_local().isoformat() + "Z"

    with get_db() as conn:
        row     = conn.execute("SELECT id FROM rooms WHERE sensor_id=?", (sensor_id,)).fetchone()
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

@bp.route("/api/measures", methods=["GET"])
def get_measures():
    return jsonify(read_measures(
        sensor_id=request.args.get("sensor_id"),
        room_id=request.args.get("room_id"),
        limit=request.args.get("limit")
    ))

@bp.route("/api/last")
def api_last():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM measures ORDER BY timestamp DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"error": "no data"}), 404
    mesure = dict(row)
    mesure["motion"] = bool(mesure["motion"])
    return jsonify({**mesure, **get_weather()})

@bp.route("/api/all")
def api_all():
    return jsonify(read_measures())

@bp.route("/api/weather")
def weather():
    return jsonify(get_weather())