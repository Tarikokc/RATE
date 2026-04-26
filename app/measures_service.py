from app.database import get_db
from app.time_helper import now_local

def append_measure(m):
    conn = get_db()
    conn.execute(
        "INSERT INTO measures (sensor_id, room_id, temp, hum, co2, motion, timestamp) VALUES (?,?,?,?,?,?,?)",
        (
            m.get("sensor_id"),
            m.get("room_id"),
            m.get("temp"),
            m.get("hum"),
            m.get("co2"),
            1 if m.get("motion") else 0,
            m.get("timestamp", now_local().isoformat() + "Z")
        )
    )
    conn.commit()

def read_measures(sensor_id=None, room_id=None, limit=None):
    q, params = "SELECT * FROM measures WHERE 1=1", []

    if sensor_id:
        q += " AND sensor_id=?"
        params.append(sensor_id)

    if room_id:
        q += " AND room_id=?"
        params.append(room_id)

    q += " ORDER BY timestamp ASC"

    if limit:
        q += f" LIMIT {int(limit)}"

    conn = get_db()
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]

    for r in rows:
        r["motion"] = bool(r["motion"])

    return rows

def get_last_measure_for_room(room_id):
    conn = get_db()

    row = conn.execute(
        "SELECT sensor_id FROM rooms WHERE id=?",
        (room_id,)
    ).fetchone()

    if not row or not row["sensor_id"]:
        return None

    m = conn.execute(
        "SELECT * FROM measures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1",
        (row["sensor_id"],)
    ).fetchone()

    if not m:
        return None

    result = dict(m)
    result["motion"] = bool(result["motion"])
    return result

def get_last_temp_for_room(room_id):
    m = get_last_measure_for_room(room_id)
    return m.get("temp") if m else None