from datetime import datetime, timedelta
import sqlite3, json

DB_FILE    = "rate.db"
DATA_FILE  = "measures.ndjson"
TARGET_TEMP = 20.0
DEG_PER_HOUR = 2.5

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_next_reservation(room_id):
    now  = datetime.utcnow().isoformat()
    soon = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    c    = get_db()
    row  = c.execute("""
        SELECT * FROM reservations
        WHERE room_id=? AND start_datetime>? AND start_datetime<=?
        ORDER BY start_datetime LIMIT 1
    """, (room_id, now, soon)).fetchone()
    c.close()
    return dict(row) if row else None

def get_current_reservation(room_id):
    now = datetime.utcnow().isoformat()
    c   = get_db()
    row = c.execute("""
        SELECT * FROM reservations
        WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
    """, (room_id, now, now)).fetchone()
    c.close()
    return dict(row) if row else None

def decide(current_temp, upcoming_res, current_res):
    now = datetime.utcnow()

    if current_res:
        end       = datetime.fromisoformat(current_res["end_datetime"].replace("Z",""))
        remaining = int((end - now).total_seconds() / 60)
        if current_temp and current_temp >= TARGET_TEMP - 0.5:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte",
                    "color": "green",  "action": "HEAT_OFF",
                    "detail": f"{current_temp}°C — fin dans {remaining} min"}
        return {"status": "EN_CHAUFFE", "label": "En chauffe",
                "color": "orange", "action": "HEAT_ON",
                "detail": f"{current_temp}°C → {TARGET_TEMP}°C — fin dans {remaining} min"}

    if upcoming_res:
        start         = datetime.fromisoformat(upcoming_res["start_datetime"].replace("Z",""))
        minutes_until = int((start - now).total_seconds() / 60)
        temp_gap      = TARGET_TEMP - (current_temp or 0)
        minutes_needed = int((temp_gap / DEG_PER_HOUR) * 60) if temp_gap > 0 else 0

        if minutes_until <= minutes_needed + 10:
            return {"status": "PRECHAUFFAGE", "label": "Préchauffage",
                    "color": "orange", "action": "HEAT_ON",
                    "detail": f"{current_temp}°C → {TARGET_TEMP}°C — résa dans {minutes_until} min"}
        wait = minutes_until - minutes_needed - 10
        return {"status": "ATTENTE", "label": f"Chauffe dans {wait} min",
                "color": "yellow", "action": "WAIT",
                "detail": f"{current_temp}°C — résa dans {minutes_until} min"}

    return {"status": "STANDBY", "label": "Standby",
            "color": "gray", "action": "HEAT_OFF",
            "detail": f"{current_temp or '--'}°C — aucune réservation"}