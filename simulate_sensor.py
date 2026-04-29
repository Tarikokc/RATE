#!/usr/bin/env python3
"""
simulate_sensor.py
──────────────────
Simule des capteurs pour tester le chauffage sans matériel.
À lancer EN PARALLÈLE du backend Flask.

    # 1. Enregistre les sensors virtuels (une seule fois)
    python simulate_sensor.py --setup

    # 2. Lance la simulation
    python simulate_sensor.py

    # Options
    python simulate_sensor.py --interval 10 --start-temp 17
"""

import argparse
import json
import logging
import os
import random
import sqlite3
import sys
import time
from datetime import datetime

DB_PATH          = os.getenv("DB_PATH",    "data/rate.db")
RELAY_STATE_FILE = os.getenv("RELAY_FILE", "data/relay_state.json")
TARGET_TEMP      = float(os.getenv("TARGET_TEMP", "20.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIM] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("Simulator")


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def get_rooms() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT id, name, sensor_id FROM rooms").fetchall()]


def register_sensor(sensor_id: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO sensors (sensor_id, last_seen) VALUES (?, ?)",
            (sensor_id, datetime.now().isoformat()),
        )


def assign_sensor_to_room(room_id: int, sensor_id: str) -> None:
    with _conn() as c:
        c.execute("UPDATE rooms SET sensor_id=? WHERE id=?", (sensor_id, room_id))


def insert_measure(sensor_id: str, room_id: int, temp: float) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO measures (sensor_id, room_id, temp, hum, co2, motion, timestamp)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                sensor_id, room_id,
                round(temp, 2),
                round(random.uniform(40, 60), 1),
                round(random.uniform(400, 900)),
                0,
                datetime.now().isoformat(),
            ),
        )


# ── Relay state ───────────────────────────────────────────────────────────────

def get_relay_state() -> dict[int, bool]:
    try:
        with open(RELAY_STATE_FILE) as f:
            return {int(k): bool(v) for k, v in json.load(f).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ── Setup mode ────────────────────────────────────────────────────────────────

def do_setup() -> None:
    rooms = get_rooms()
    if not rooms:
        log.error("Aucune salle trouvée. Crée d'abord des salles via l'API.")
        sys.exit(1)

    log.info("── Setup : enregistrement des sensors virtuels ──")
    for room in rooms:
        sid = f"sim-room-{room['id']}"
        register_sensor(sid)
        assign_sensor_to_room(room["id"], sid)
        log.info(f"  '{room['name']}' (id={room['id']}) → sensor_id='{sid}'")
    log.info("Setup terminé ✓ — Lance maintenant : python simulate_sensor.py")


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate(interval: int, start_temp: float) -> None:
    rooms = [r for r in get_rooms() if r["sensor_id"]]

    if not rooms:
        log.error(
            "Aucune salle avec sensor_id.\n"
            "Lance d'abord : python simulate_sensor.py --setup"
        )
        sys.exit(1)

    temps: dict[int, float] = {r["id"]: start_temp for r in rooms}

    log.info(f"Simulation démarrée — {len(rooms)} salle(s) | interval={interval}s | target={TARGET_TEMP}°C")
    for r in rooms:
        log.info(f"  • {r['name']:15s} sensor={r['sensor_id']}")
    log.info("Ctrl+C pour arrêter\n")

    while True:
        relay = get_relay_state()
        print(f"── {datetime.now().strftime('%H:%M:%S')} {'─' * 40}")

        for room in rooms:
            rid = room["id"]
            on  = relay.get(rid, False)

            if on:
                temps[rid] += random.uniform(0.08, 0.15)   # ~+1°C / 5 min
            else:
                temps[rid] -= random.uniform(0.02, 0.06)   # ~-0.3°C / 5 min

            temps[rid] = round(max(13.0, min(35.0, temps[rid])), 2)
            insert_measure(room["sensor_id"], rid, temps[rid])

            bar_len  = 20
            filled   = max(0, min(bar_len, int((temps[rid] - 13) / (35 - 13) * bar_len)))
            bar      = "█" * filled + "░" * (bar_len - filled)
            icon     = "🔥" if on else "❄️ "
            log.info(f"  {icon} {room['name']:15s} [{bar}] {temps[rid]:5.1f}°C")

        print()
        time.sleep(interval)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur capteur RATE")
    parser.add_argument("--interval",   type=int,   default=30,   help="Secondes entre mesures (défaut: 30)")
    parser.add_argument("--start-temp", type=float, default=17.0, help="Température initiale (défaut: 17.0)")
    parser.add_argument("--setup",      action="store_true",      help="Enregistre les sensors virtuels")
    args = parser.parse_args()

    if args.setup:
        do_setup()
    else:
        try:
            simulate(args.interval, args.start_temp)
        except KeyboardInterrupt:
            log.info("\nSimulateur arrêté proprement.")
