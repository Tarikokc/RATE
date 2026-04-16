from datetime import datetime, timedelta
import sqlite3

DB_FILE     = "rate.db"
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
