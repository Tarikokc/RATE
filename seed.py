import sqlite3
from datetime import datetime, timedelta

DB_FILE = "rate.db"

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Génère une datetime ISO à partir d'aujourd'hui + offset
def dt(day_offset=0, hour=8, minute=0):
    d = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    d += timedelta(days=day_offset)
    return d.isoformat()

reservations = [
    # ── Aujourd'hui ──────────────────────────────────
    { "room_id": 1, "user_name": "M. Martin",  "title": "Cours de Maths",         "start": dt(0, 8,  0),  "end": dt(0, 10, 0),  "people": 28 },
    { "room_id": 1, "user_name": "Mme Dupont", "title": "TP Python",               "start": dt(0, 14, 0),  "end": dt(0, 16, 0),  "people": 25 },
    { "room_id": 2, "user_name": "M. Bernard", "title": "Cours de Physique",       "start": dt(0, 9,  0),  "end": dt(0, 11, 0),  "people": 18 },
    { "room_id": 3, "user_name": "Direction",  "title": "Réunion de direction",    "start": dt(0, 10, 0),  "end": dt(0, 12, 0),  "people": 8  },
    { "room_id": 4, "user_name": "M. Leroy",   "title": "Conférence IoT",          "start": dt(0, 15, 0),  "end": dt(0, 17, 0),  "people": 80 },

    # ── Demain ───────────────────────────────────────
    { "room_id": 1, "user_name": "Mme Petit",  "title": "Cours d'Anglais",         "start": dt(1, 8,  0),  "end": dt(1, 9,  30), "people": 30 },
    { "room_id": 1, "user_name": "M. Martin",  "title": "Examen de Maths",         "start": dt(1, 10, 0),  "end": dt(1, 12, 0),  "people": 30 },
    { "room_id": 2, "user_name": "M. Bernard", "title": "TP Electronique",         "start": dt(1, 13, 0),  "end": dt(1, 15, 0),  "people": 15 },
    { "room_id": 3, "user_name": "RH",         "title": "Entretiens annuels",      "start": dt(1, 9,  0),  "end": dt(1, 18, 0),  "people": 4  },
    { "room_id": 4, "user_name": "Asso RATE",  "title": "Présentation projet IA",  "start": dt(1, 14, 0),  "end": dt(1, 16, 0),  "people": 60 },

    # ── Après-demain ─────────────────────────────────
    { "room_id": 1, "user_name": "M. Durand",  "title": "Cours de Réseau",         "start": dt(2, 8,  0),  "end": dt(2, 10, 0),  "people": 22 },
    { "room_id": 2, "user_name": "Mme Moreau", "title": "TP Capteurs IoT",         "start": dt(2, 10, 0),  "end": dt(2, 12, 0),  "people": 12 },
    { "room_id": 4, "user_name": "M. Simon",   "title": "Formation DevOps",        "start": dt(2, 9,  0),  "end": dt(2, 17, 0),  "people": 45 },
]

c = db()
inserted = 0
skipped  = 0

for r in reservations:
    conflict = c.execute("""
        SELECT id FROM reservations
        WHERE room_id=?
          AND NOT (end_datetime <= ? OR start_datetime >= ?)
    """, (r["room_id"], r["start"], r["end"])).fetchone()

    if conflict:
        print(f"⚠️  Conflit ignoré : {r['title']} ({r['start']})")
        skipped += 1
        continue

    c.execute("""
        INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (r["room_id"], r["user_name"], r["title"], r["start"], r["end"], r["people"]))
    inserted += 1

c.commit()
c.close()
print(f"\n✅ {inserted} réservations insérées, {skipped} conflits ignorés.")
