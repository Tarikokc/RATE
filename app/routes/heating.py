from flask import Blueprint, jsonify
from app.database import get_db
from app.measures_service import get_last_temp_for_room
from app.heating_controller import heating_decision, get_next_reservation, get_current_reservation

bp = Blueprint("heating", __name__)

@bp.route("/api/heating/decision")
def heating_decision_api():
    conn = get_db()
    rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms").fetchall()]

    return jsonify([
        {
            "room": room["name"],
            "current_temp": (temp := get_last_temp_for_room(room["id"])),
            "decision": heating_decision(
                temp,
                get_next_reservation(room["id"]),
                get_current_reservation(room["id"])
            )
        }
        for room in rooms
    ])    