#!/usr/bin/env python3
"""
simulate_sensor.py
──────────────────
Simule tous les capteurs présents dans la table `sensors`.
À lancer EN PARALLÈLE du backend Flask.

Comportement :
  - Capteur assigné à une salle  → température réagit aux décisions de chauffage (relay_state.json)
  - Capteur non assigné           → mesures aléatoires stables (humidite, CO2, temp neutre)

Usage :
    python simulate_sensor.py
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


def load_simulation_targets() -> list[dict]:
    """
    Construit la liste des cibles à simuler depuis la DB.

    Retourne une liste de dicts :
      {
        sensor_id : str,
        room_id   : int | None,
        room_name : str | None,
      }
    """
    with _conn() as c:
        sensors = [dict(r) for r in c.execute("SELECT sensor_id FROM sensors").fetchall()]
        # Map sensor_id -> room (si assigné)
        rooms = [
            dict(r) for r in
            c.execute("SELECT id, name, sensor_id FROM rooms WHERE sensor_id IS NOT NULL AND sensor_id != ''").fetchall()
        ]

    room_by_sensor: dict[str, dict] = {r["sensor_id"]: r for r in rooms}

    targets = []
    for s in sensors:
        sid  = s["sensor_id"]
        room = room_by_sensor.get(sid)
        targets.append({
            "sensor_id": sid,
            "room_id"  : room["id"]   if room else None,
            "room_name": room["name"] if room else None,
        })
    return targets


def insert_measure(sensor_id: str, room_id: int | None, temp: float) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO measures (sensor_id, room_id, temp, hum, co2, motion, timestamp)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                sensor_id,
                room_id,
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


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate(interval: int, start_temp: float) -> None:
    targets = load_simulation_targets()

    if not targets:
        log.error(
            "Aucun capteur trouvé dans la table `sensors`.\n"
            "Ajoute d'abord un capteur via l'API ou insere-le manuellement en DB."
        )
        sys.exit(1)

    assigned   = [t for t in targets if t["room_id"] is not None]
    unassigned = [t for t in targets if t["room_id"] is None]

    log.info(f"Simulation démarrée — {len(targets)} capteur(s) | interval={interval}s | target={TARGET_TEMP}°C")

    if assigned:
        log.info(f"  🏠 {len(assigned)} assigné(s) à une salle (réagissent au chauffage) :")
        for t in assigned:
            log.info(f"      • {t['room_name']:15s}  sensor={t['sensor_id']}")

    if unassigned:
        log.info(f"  🔌 {len(unassigned)} non assigné(s) (mesures aléatoires) :")
        for t in unassigned:
            log.info(f"      • sensor={t['sensor_id']}")

    log.info("Ctrl+C pour arrêter\n")

    # Temp initiale par capteur
    temps: dict[str, float] = {t["sensor_id"]: start_temp for t in targets}

    while True:
        relay = get_relay_state()
        print(f"── {datetime.now().strftime('%H:%M:%S')} {'─' * 40}")

        for t in targets:
            sid     = t["sensor_id"]
            rid     = t["room_id"]
            on      = relay.get(rid, False) if rid is not None else False
            label   = t["room_name"] if t["room_name"] else f"[{sid}]"

            if rid is not None:
                # Capteur assigné : temp réagit au relais
                if on:
                    temps[sid] += random.uniform(0.08, 0.15)   # ~+1°C / 5 min
                else:
                    temps[sid] -= random.uniform(0.02, 0.06)   # ~-0.3°C / 5 min
                temps[sid] = round(max(13.0, min(35.0, temps[sid])), 2)
                icon = "🔥" if on else "❄️ "
            else:
                # Capteur non assigné : légère variation aléatoire autour de start_temp
                temps[sid] += random.uniform(-0.05, 0.05)
                temps[sid] = round(max(13.0, min(35.0, temps[sid])), 2)
                icon = "🔌"

            insert_measure(sid, rid, temps[sid])

            bar_len = 20
            filled  = max(0, min(bar_len, int((temps[sid] - 13) / (35 - 13) * bar_len)))
            bar     = "█" * filled + "░" * (bar_len - filled)
            log.info(f"  {icon} {label:18s} [{bar}] {temps[sid]:5.1f}°C")

        print()
        time.sleep(interval)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulateur capteur RATE")
    parser.add_argument("--interval",   type=int,   default=30,   help="Secondes entre mesures (défaut: 30)")
    parser.add_argument("--start-temp", type=float, default=17.0, help="Température initiale (défaut: 17.0)")
    args = parser.parse_args()

    try:
        simulate(args.interval, args.start_temp)
    except KeyboardInterrupt:
        log.info("\nSimulateur arrêté proprement.")
