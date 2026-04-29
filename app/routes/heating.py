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


@bp.route("/api/heating/state")
def heating_relay_state():
    """État actuel des relais (utile pour debug et dashboard)."""
    from app.heating_loop import get_relay_state
    return jsonify({str(k): v for k, v in get_relay_state().items()})


@bp.route("/api/heating/trigger", methods=["POST"])
def heating_trigger():
    """Force un run immédiat du heating loop (utile pour les tests)."""
    from app.heating_loop import run_once
    run_once()
    return jsonify({"ok": True, "message": "Heating loop exécuté"})
