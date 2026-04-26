from flask import Blueprint, request, jsonify
from datetime import timedelta
from app.database import get_db
from app.measures_service import get_last_measure_for_room
from app.heating_controller import heating_decision, TARGET_TEMP
from app.time_helper import now_local

bp = Blueprint("rooms", __name__)

@bp.route("/api/rooms", methods=["GET"])
def get_rooms():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM rooms ORDER BY floor, name").fetchall()]
    return jsonify(rows)

@bp.route("/api/rooms", methods=["POST"])
def create_room():
    d = request.get_json(force=True)
    sensor_id = d.get("sensor_id") or None

    if not d.get("name"):
        return jsonify({"error": "name est requis"}), 400

    conn = get_db()

    if sensor_id:
        if not conn.execute(
            "SELECT 1 FROM sensors WHERE sensor_id=?",
            (sensor_id,)
        ).fetchone():
            return jsonify({"error": "Capteur introuvable ou jamais détecté"}), 400

        if conn.execute(
            "SELECT 1 FROM rooms WHERE sensor_id=?",
            (sensor_id,)
        ).fetchone():
            return jsonify({"error": "Capteur déjà associé à une autre salle"}), 409

    cur = conn.execute(
        "INSERT INTO rooms (name, capacity, floor, description, sensor_id) VALUES (?,?,?,?,?)",
        (
            d["name"],
            d.get("capacity", 10),
            d.get("floor", "RDC"),
            d.get("description", ""),
            sensor_id
        )
    )
    conn.commit()

    room_id = cur.lastrowid
    return jsonify({"id": room_id, **d, "sensor_id": sensor_id}), 201

@bp.route("/api/rooms/<int:rid>", methods=["PATCH"])
def update_room(rid):
    d = request.get_json(force=True)
    sensor_id = d.get("sensor_id") or None

    conn = get_db()

    if sensor_id:
        if not conn.execute(
            "SELECT 1 FROM sensors WHERE sensor_id=?",
            (sensor_id,)
        ).fetchone():
            return jsonify({"error": "Capteur introuvable ou jamais détecté"}), 400

        if conn.execute(
            "SELECT id FROM rooms WHERE sensor_id=? AND id!=?",
            (sensor_id, rid)
        ).fetchone():
            return jsonify({"error": "Capteur déjà associé à une autre salle"}), 409

    conn.execute("UPDATE rooms SET sensor_id=? WHERE id=?", (sensor_id, rid))
    conn.commit()
    return jsonify({"ok": True})

@bp.route("/api/rooms/<int:rid>", methods=["DELETE"])
def delete_room(rid):
    conn = get_db()
    conn.execute("DELETE FROM rooms WHERE id=?", (rid,))
    conn.commit()
    return "", 204

@bp.route("/api/rooms/status", methods=["GET"])
def rooms_status():
    now = now_local().isoformat()
    soon = (now_local() + timedelta(hours=1)).isoformat()
    result = []

    conn = get_db()
    rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms").fetchall()]

    for room in rooms:
        current = conn.execute("""
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

        measure = get_last_measure_for_room(room["id"])
        current_temp = measure.get("temp") if measure else None

        result.append({
            **room,
            "temp": measure.get("temp") if measure else None,
            "hum": measure.get("hum") if measure else None,
            "co2": measure.get("co2") if measure else None,
            "motion": measure.get("motion") if measure else None,
            "last_measure": measure,
            "current_temp": current_temp,
            "target_temp": TARGET_TEMP,
            "current_reservation": dict(current) if current else None,
            "upcoming_reservation": dict(upcoming) if upcoming else None,
            "next_reservation": dict(next_any) if next_any else None,
            "heating": heating_decision(
                current_temp,
                dict(upcoming) if upcoming else None,
                dict(current) if current else None
            )
        })

    return jsonify(result)