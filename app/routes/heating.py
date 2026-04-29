from flask import Blueprint, jsonify, request
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


@bp.route("/api/heating/sensor-state")
def heating_sensor_state():
    """
    Retourne l'état du relais pour un sensor_id donné.
    L'ESP l'appelle après chaque POST /api/measures pour savoir
    si son relais est ON ou OFF sans connaître son room_id.

    GET /api/heating/sensor-state?sensor_id=esp8266-abc123
    → {"on": true}  ou  {"on": false}
    """
    sensor_id = request.args.get("sensor_id", "")
    if not sensor_id:
        return jsonify({"error": "sensor_id requis"}), 400

    conn = get_db()
    row  = conn.execute(
        "SELECT id FROM rooms WHERE sensor_id = ? LIMIT 1", (sensor_id,)
    ).fetchone()

    if not row:
        return jsonify({"on": False})  # capteur inconnu → éteint par défaut

    from app.heating_loop import get_relay_state
    on = get_relay_state().get(row["id"], False)
    return jsonify({"on": on})


@bp.route("/api/heating/trigger", methods=["POST"])
def heating_trigger():
    """Force un run immédiat du heating loop (utile pour les tests)."""
    from app.heating_loop import run_once
    run_once()
    return jsonify({"ok": True, "message": "Heating loop exécuté"})
