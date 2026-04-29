# Boucle d'automatisation du chauffage — APScheduler + GPIO (ou mock)
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta

from app.config import Config
from app.heating_controller import heating_decision

log = logging.getLogger("HeatingLoop")

# GPIO avec fallback mock automatique
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    log.info("[GPIO] RPi.GPIO natif chargé")
except ImportError:
    from app import gpio_mock as GPIO  # type: ignore
    log.info("[GPIO] Mock activé (pas de Pi détecté)")

# Mapping room_id → broche GPIO (adapter selon câblage physique)
ROOM_PINS: dict[int, int] = {
    1: 17,
    2: 27,
    3: 22,
}

# État partagé avec simulate_sensor.py via fichier JSON
_relay_state: dict[int, bool] = {}
RELAY_STATE_FILE = "data/relay_state.json"


def _save_relay_state() -> None:
    os.makedirs("data", exist_ok=True)
    with open(RELAY_STATE_FILE, "w") as f:
        json.dump(_relay_state, f)


def _set_relay(room_id: int, on: bool) -> None:
    if _relay_state.get(room_id) == on:
        return  # Pas de changement → on évite un GPIO inutile
    pin = ROOM_PINS.get(room_id)
    if pin is not None:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, on)
    _relay_state[room_id] = on
    _save_relay_state()
    log.info(f"  Room {room_id} → {'🔥 HEAT ON ' if on else '❄️  HEAT OFF'}")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_once() -> None:
    """Évalue et applique les décisions de chauffage pour toutes les salles."""
    now  = datetime.now().isoformat()
    soon = (datetime.now() + timedelta(hours=2)).isoformat()

    conn = _get_conn()
    try:
        rooms = [dict(r) for r in conn.execute("SELECT id, name FROM rooms").fetchall()]
        for room in rooms:
            rid  = room["id"]
            name = room["name"]

            # Température actuelle via sensor_id
            row  = conn.execute("SELECT sensor_id FROM rooms WHERE id=?", (rid,)).fetchone()
            temp = None
            if row and row["sensor_id"]:
                m = conn.execute(
                    "SELECT temp FROM measures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1",
                    (row["sensor_id"],),
                ).fetchone()
                temp = m["temp"] if m else None

            # Réservation en cours
            current = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
            """, (rid, now, now)).fetchone()

            # Prochaine réservation (dans les 2h)
            upcoming = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=? AND start_datetime>? AND start_datetime<=?
                ORDER BY start_datetime LIMIT 1
            """, (rid, now, soon)).fetchone()

            decision = heating_decision(
                temp,
                dict(upcoming) if upcoming else None,
                dict(current)  if current  else None,
            )
            action = decision.get("action")

            log.info(
                f"  [{name}] temp={f'{temp}°C' if temp else '--':>6} | "
                f"{decision['label']:20s} | {decision['detail']}"
            )

            if action == "HEAT_ON":
                _set_relay(rid, True)
            elif action == "HEAT_OFF":
                _set_relay(rid, False)
    finally:
        conn.close()


def get_relay_state() -> dict[int, bool]:
    return dict(_relay_state)


def start_scheduler() -> None:
    """À appeler depuis server.py après la création de l'app Flask."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_once, "interval", minutes=5, id="heating_loop", replace_existing=True)
    scheduler.start()
    log.info("[HeatingLoop] Scheduler démarré — évaluation toutes les 5 min")
    run_once()  # Premier run immédiat au démarrage
