from datetime import datetime, timedelta
from app.database import get_db
from app.time_helper import now_local

TARGET_TEMP      = 20.0
HEAT_ADVANCE_MIN = 60
DEG_PER_HOUR     = 2.5
TEMP_TOLERANCE   = 0.5

def get_next_reservation(room_id):
    now  = now_local()
    soon = (now + timedelta(hours=2)).isoformat()
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime>? AND start_datetime<=?
            ORDER BY start_datetime LIMIT 1
        """, (room_id, now.isoformat(), soon)).fetchone()
    return dict(row) if row else None

def get_current_reservation(room_id):
    now = now_local().isoformat()
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM reservations
            WHERE room_id=? AND start_datetime<=? AND end_datetime>=?
        """, (room_id, now, now)).fetchone()
    return dict(row) if row else None

def heating_decision(current_temp, upcoming_res, current_res):
    now = now_local()

    if current_temp is not None and current_temp > TARGET_TEMP + 5:
        return {"status": "SURCHAUFFE", "label": "Surchauffe ⚠️", "color": "red",
                "detail": f"{current_temp}°C — dépasse le seuil ({TARGET_TEMP + 5}°C)", "action": "HEAT_OFF"}

    if current_res:
        end       = datetime.fromisoformat(current_res["end_datetime"].replace("Z", ""))
        remaining = int((end - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "OCCUPE", "label": "Occupée", "color": "blue",
                    "detail": f"Fin dans {remaining} min", "action": None}
        if current_temp >= TARGET_TEMP - TEMP_TOLERANCE:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}°C / {TARGET_TEMP}°C — fin dans {remaining} min", "action": None}
        return {"status": "EN_CHAUFFE", "label": "En chauffe", "color": "orange",
                "detail": f"{current_temp}°C → {TARGET_TEMP}°C — fin dans {remaining} min", "action": "HEAT_ON"}

    if upcoming_res:
        start         = datetime.fromisoformat(upcoming_res["start_datetime"].replace("Z", ""))
        minutes_until = int((start - now).total_seconds() / 60)
        if current_temp is None:
            return {"status": "PRECHAUFFAGE", "label": "Préchauffage", "color": "orange",
                    "detail": f"Résa dans {minutes_until} min", "action": "HEAT_ON"}
        temp_gap = TARGET_TEMP - current_temp
        if temp_gap <= 0:
            return {"status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                    "detail": f"{current_temp}°C — prêt avant {start.strftime('%H:%M')}", "action": None}
        minutes_needed = int((temp_gap / DEG_PER_HOUR) * 60)
        if minutes_until <= minutes_needed + 10:
            return {"status": "PRECHAUFFAGE", "label": "Préchauffage", "color": "orange",
                    "detail": f"{current_temp}°C → {TARGET_TEMP}°C — résa dans {minutes_until} min ({minutes_needed} min de chauffe)",
                    "action": "HEAT_ON"}
        wait = minutes_until - minutes_needed - 10
        return {"status": "ATTENTE", "label": f"Chauffe dans {wait} min", "color": "yellow",
                "detail": f"{current_temp}°C — résa dans {minutes_until} min", "action": "WAIT"}

    return {"status": "STANDBY", "label": "Standby", "color": "gray",
            "detail": f"{current_temp if current_temp else '--'}°C — aucune résa", "action": None}