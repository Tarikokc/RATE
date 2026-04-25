from flask import Blueprint, jsonify
from app.database import get_db

bp = Blueprint("sensors", __name__)

@bp.route("/api/sensors/available", methods=["GET"])
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

@bp.route("/api/sensors", methods=["GET"])
def get_sensors():
    with get_db() as conn:
        rows = conn.execute("SELECT sensor_id, last_seen FROM sensors ORDER BY last_seen DESC").fetchall()
    return jsonify([dict(r) for r in rows])