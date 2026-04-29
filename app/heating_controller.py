from datetime import datetime, timedelta
from app.database import get_db
from app.time_helper import now_local, to_local
from app.config import Config

TARGET_TEMP      = Config.TARGET_TEMP
HEAT_ADVANCE_MIN = Config.HEAT_ADVANCE_MIN
DEG_PER_HOUR     = Config.DEG_PER_HOUR
TEMP_TOLERANCE   = Config.TEMP_TOLERANCE


def _parse_dt(raw: str) -> datetime:
    """
    Parse un datetime stocké en DB (UTC, avec ou sans 'Z' / '+00:00')
    et le retourne en heure locale Paris (naive datetime).
    Exemples acceptés :
        '2026-04-29T21:00:00.000Z'
        '2026-04-29T21:00:00'
        '2026-04-30T14:00:00+00:00'
    """
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        dt = datetime.fromisoformat(raw.replace("+00:00", ""))

    # Si le datetime est naive (pas de tzinfo), on suppose UTC
    if dt.tzinfo is None:
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)

    return to_local(dt.replace(tzinfo=None) if dt.tzinfo is None else
                    dt.astimezone(__import__('pytz').utc).replace(tzinfo=None))


def get_next_reservation(room_id):
    now  = now_local()
    soon = now + timedelta(hours=2)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reservations WHERE room_id=? ORDER BY start_datetime",
        (room_id,)
    ).fetchall()
    for row in rows:
        r = dict(row)
        start = _parse_dt(r["start_datetime"])
        if now < start <= soon:
            return r
    return None


def get_current_reservation(room_id):
    now  = now_local()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM reservations WHERE room_id=? ORDER BY start_datetime",
        (room_id,)
    ).fetchall()
    for row in rows:
        r     = dict(row)
        start = _parse_dt(r["start_datetime"])
        end   = _parse_dt(r["end_datetime"])
        if start <= now <= end:
            return r
    return None


def heating_decision(current_temp, upcoming_res, current_res):
    now = now_local()

    if current_temp is not None and current_temp > TARGET_TEMP + 5:
        return {
            "status": "SURCHAUFFE", "label": "Surchauffe \u26a0\ufe0f", "color": "red",
            "detail": f"{current_temp}\u00b0C \u2014 d\u00e9passe le seuil ({TARGET_TEMP + 5}\u00b0C)",
            "action": "HEAT_OFF"
        }

    if current_res:
        end       = _parse_dt(current_res["end_datetime"])
        remaining = int((end - now).total_seconds() / 60)

        if current_temp is None:
            return {
                "status": "OCCUPE", "label": "Occup\u00e9e", "color": "blue",
                "detail": f"Fin dans {remaining} min", "action": None
            }
        if current_temp >= TARGET_TEMP - TEMP_TOLERANCE:
            return {
                "status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                "detail": f"{current_temp}\u00b0C / {TARGET_TEMP}\u00b0C \u2014 fin dans {remaining} min",
                "action": None
            }
        return {
            "status": "EN_CHAUFFE", "label": "En chauffe", "color": "orange",
            "detail": f"{current_temp}\u00b0C \u2192 {TARGET_TEMP}\u00b0C \u2014 fin dans {remaining} min",
            "action": "HEAT_ON"
        }

    if upcoming_res:
        start         = _parse_dt(upcoming_res["start_datetime"])
        minutes_until = int((start - now).total_seconds() / 60)

        if current_temp is None:
            return {
                "status": "PRECHAUFFAGE", "label": "Pr\u00e9chauffage", "color": "orange",
                "detail": f"R\u00e9sa dans {minutes_until} min", "action": "HEAT_ON"
            }

        temp_gap = TARGET_TEMP - current_temp
        if temp_gap <= 0:
            return {
                "status": "CIBLE_ATTEINTE", "label": "Cible atteinte", "color": "green",
                "detail": f"{current_temp}\u00b0C \u2014 pr\u00eat avant {start.strftime('%H:%M')}",
                "action": None
            }

        minutes_needed = int((temp_gap / DEG_PER_HOUR) * 60)
        if minutes_until <= minutes_needed + 10:
            return {
                "status": "PRECHAUFFAGE", "label": "Pr\u00e9chauffage", "color": "orange",
                "detail": (
                    f"{current_temp}\u00b0C \u2192 {TARGET_TEMP}\u00b0C \u2014 r\u00e9sa dans {minutes_until} min "
                    f"({minutes_needed} min de chauffe)"
                ),
                "action": "HEAT_ON"
            }

        wait = minutes_until - minutes_needed - 10
        return {
            "status": "ATTENTE", "label": f"Chauffe dans {wait} min", "color": "yellow",
            "detail": f"{current_temp}\u00b0C \u2014 r\u00e9sa dans {minutes_until} min",
            "action": "WAIT"
        }

    return {
        "status": "STANDBY", "label": "Standby", "color": "gray",
        "detail": f"{current_temp if current_temp else '--'}\u00b0C \u2014 aucune r\u00e9sa",
        "action": None
    }
