# Boucle d'automatisation du chauffage — APScheduler + GPIO (ou mock)
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta, timezone

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

# État partagé en mémoire + fichier JSON
_relay_state: dict[int, bool] = {}
RELAY_STATE_FILE = "data/relay_state.json"


def _save_relay_state() -> None:
    os.makedirs("data", exist_ok=True)
    with open(RELAY_STATE_FILE, "w") as f:
        json.dump(_relay_state, f)


def _set_relay(room_id: int, on: bool) -> None:
    if _relay_state.get(room_id) == on:
        return
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


def _utc_str(dt: datetime) -> str:
    """
    Retourne un datetime UTC sous la forme acceptée par SQLite pour
    comparer avec les valeurs stockées ('2026-04-29T21:00:00.000Z').
    On utilise le format ISO sans 'Z' car SQLite compare en string.
    Exemple : '2026-04-29T20:45:00'
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def run_once() -> None:
    """Evalue et applique les décisions de chauffage pour toutes les salles."""
    # Toutes les comparaisons en UTC pour correspondre aux datetimes en DB
    now_utc  = datetime.now(timezone.utc)
    now_str  = _utc_str(now_utc)
    soon_str = _utc_str(now_utc + timedelta(hours=2))

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
            # Les datetimes DB sont UTC (ex: '2026-04-29T21:00:00.000Z')
            # On retire le 'Z' pour la comparaison string avec now_str
            current = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=?
                  AND replace(start_datetime,'Z','') <= ?
                  AND replace(end_datetime,  'Z','') >= ?
            """, (rid, now_str, now_str)).fetchone()

            # Prochaine réservation (dans les 2h)
            upcoming = conn.execute("""
                SELECT * FROM reservations
                WHERE room_id=?
                  AND replace(start_datetime,'Z','') > ?
                  AND replace(start_datetime,'Z','') <= ?
                ORDER BY start_datetime LIMIT 1
            """, (rid, now_str, soon_str)).fetchone()

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
    """A appeler depuis server.py après la création de l'app Flask."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_once, "interval", minutes=5, id="heating_loop", replace_existing=True)
    scheduler.start()
    log.info("[HeatingLoop] Scheduler démarré — évaluation toutes les 5 min")
    run_once()  # Premier run immédiat au démarrage
