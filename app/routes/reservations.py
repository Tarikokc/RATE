from flask import Blueprint, request, jsonify
from app.database import get_db

bp = Blueprint("reservations", __name__)

@bp.route("/api/reservations", methods=["GET"])
def get_reservations():
    date    = request.args.get("date")
    room_id = request.args.get("room_id")
    q       = """
        SELECT r.*, rm.name AS room_name, rm.capacity, rm.floor
        FROM reservations r JOIN rooms rm ON r.room_id = rm.id
        WHERE 1=1
    """
    params = []
    if date:
        q += " AND DATE(r.start_datetime) = ?"; params.append(date)
    if room_id:
        q += " AND r.room_id = ?"; params.append(int(room_id))
    q += " ORDER BY r.start_datetime"
    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    return jsonify(rows)

@bp.route("/api/reservations", methods=["POST"])
def create_reservation():
    d = request.get_json(force=True)
    with get_db() as conn:
        conflict = conn.execute("""
            SELECT id FROM reservations
            WHERE room_id=? AND NOT (end_datetime<=? OR start_datetime>=?)
        """, (d["room_id"], d["start_datetime"], d["end_datetime"])).fetchone()
        if conflict:
            return jsonify({"error": "Créneau déjà réservé pour cette salle"}), 409
        cur    = conn.execute(
            "INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count) VALUES (?,?,?,?,?,?)",
            (d["room_id"], d["user_name"], d["title"], d["start_datetime"], d["end_datetime"], d.get("people_count", 1))
        )
        new_id = cur.lastrowid
    return jsonify({**d, "id": new_id}), 201

@bp.route("/api/reservations/<int:rid>", methods=["DELETE"])
def delete_reservation(rid):
    with get_db() as conn:
        conn.execute("DELETE FROM reservations WHERE id=?", (rid,))
    return "", 204