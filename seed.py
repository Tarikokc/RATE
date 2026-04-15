# import sqlite3
# from datetime import datetime, timedelta

# DB_FILE = "rate.db"

# def db():
#     conn = sqlite3.connect(DB_FILE)
#     conn.row_factory = sqlite3.Row
#     return conn

# # Génère une datetime ISO à partir d'aujourd'hui + offset
# def dt(day_offset=0, hour=8, minute=0):
#     d = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
#     d += timedelta(days=day_offset)
#     return d.isoformat()

# reservations = [
#     # ── Aujourd'hui ──────────────────────────────────
#     { "room_id": 1, "user_name": "M. Martin",  "title": "Cours de Maths",         "start": dt(0, 8,  0),  "end": dt(0, 10, 0),  "people": 28 },
#     { "room_id": 1, "user_name": "Mme Dupont", "title": "TP Python",               "start": dt(0, 14, 0),  "end": dt(0, 16, 0),  "people": 25 },
#     { "room_id": 2, "user_name": "M. Bernard", "title": "Cours de Physique",       "start": dt(0, 9,  0),  "end": dt(0, 11, 0),  "people": 18 },
#     { "room_id": 3, "user_name": "Direction",  "title": "Réunion de direction",    "start": dt(0, 10, 0),  "end": dt(0, 12, 0),  "people": 8  },
#     { "room_id": 4, "user_name": "M. Leroy",   "title": "Conférence IoT",          "start": dt(0, 15, 0),  "end": dt(0, 17, 0),  "people": 80 },

#     # ── Demain ───────────────────────────────────────
#     { "room_id": 1, "user_name": "Mme Petit",  "title": "Cours d'Anglais",         "start": dt(1, 8,  0),  "end": dt(1, 9,  30), "people": 30 },
#     { "room_id": 1, "user_name": "M. Martin",  "title": "Examen de Maths",         "start": dt(1, 10, 0),  "end": dt(1, 12, 0),  "people": 30 },
#     { "room_id": 2, "user_name": "M. Bernard", "title": "TP Electronique",         "start": dt(1, 13, 0),  "end": dt(1, 15, 0),  "people": 15 },
#     { "room_id": 3, "user_name": "RH",         "title": "Entretiens annuels",      "start": dt(1, 9,  0),  "end": dt(1, 18, 0),  "people": 4  },
#     { "room_id": 4, "user_name": "Asso RATE",  "title": "Présentation projet IA",  "start": dt(1, 14, 0),  "end": dt(1, 16, 0),  "people": 60 },

#     # ── Après-demain ─────────────────────────────────
#     { "room_id": 1, "user_name": "M. Durand",  "title": "Cours de Réseau",         "start": dt(2, 8,  0),  "end": dt(2, 10, 0),  "people": 22 },
#     { "room_id": 2, "user_name": "Mme Moreau", "title": "TP Capteurs IoT",         "start": dt(2, 10, 0),  "end": dt(2, 12, 0),  "people": 12 },
#     { "room_id": 4, "user_name": "M. Simon",   "title": "Formation DevOps",        "start": dt(2, 9,  0),  "end": dt(2, 17, 0),  "people": 45 },
# ]

# c = db()
# inserted = 0
# skipped  = 0

# for r in reservations:
#     conflict = c.execute("""
#         SELECT id FROM reservations
#         WHERE room_id=?
#           AND NOT (end_datetime <= ? OR start_datetime >= ?)
#     """, (r["room_id"], r["start"], r["end"])).fetchone()

#     if conflict:
#         print(f"⚠️  Conflit ignoré : {r['title']} ({r['start']})")
#         skipped += 1
#         continue

#     c.execute("""
#         INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count)
#         VALUES (?, ?, ?, ?, ?, ?)
#     """, (r["room_id"], r["user_name"], r["title"], r["start"], r["end"], r["people"]))
#     inserted += 1

# c.commit()
# c.close()
# print(f"\n✅ {inserted} réservations insérées, {skipped} conflits ignorés.")

import json, sqlite3, os
from datetime import datetime, timedelta

DATA_FILE = "measures.ndjson"
DB_FILE   = "rate.db"

# ─── 1. Mesures par salle ──────────────────────────────
# room_id 1 → A101 : 16°C  (froid, besoin de chauffer)
# room_id 2 → A102 : 22°C  (cible atteinte)
# room_id 3 → B201 : 14°C  (très froid)
# room_id 4 → Amphi: 31°C  (surchauffe)

test_measures = [
    {"room_id": 1, "sensor_id": "rpi5-room-1", "temp": 16.2, "hum": 55, "co2": 620, "motion": False},
    {"room_id": 2, "sensor_id": "rpi5-room-2", "temp": 22.1, "hum": 48, "co2": 580, "motion": True},
    {"room_id": 3, "sensor_id": "rpi5-room-3", "temp": 14.5, "hum": 60, "co2": 550, "motion": False},
    {"room_id": 4, "sensor_id": "rpi5-room-4", "temp": 31.8, "hum": 40, "co2": 700, "motion": True},
]

now = datetime.utcnow()

with open(DATA_FILE, "a", encoding="utf-8") as f:
    for m in test_measures:
        m["timestamp"] = now.isoformat() + "Z"
        f.write(json.dumps(m) + "\n")

print("✅ Mesures insérées dans measures.ndjson")


# ─── 2. Réservations de test ───────────────────────────
conn = sqlite3.connect(DB_FILE)

# Nettoie les réservations de test précédentes
conn.execute("DELETE FROM reservations WHERE title LIKE '[TEST]%'")

reservations = [
    # A101 : résa dans 20 min → doit déclencher PRECHAUFFAGE (16°C, besoin de monter à 20°C)
    {
        "room_id": 1,
        "user_name": "Test User",
        "title": "[TEST] Cours Angular",
        "start_datetime": (now + timedelta(minutes=20)).isoformat() + "Z",
        "end_datetime":   (now + timedelta(minutes=80)).isoformat() + "Z",
        "people_count": 15
    },
    # A102 : résa en cours → CIBLE_ATTEINTE (22°C, au-dessus de 20°C)
    {
        "room_id": 2,
        "user_name": "Test User",
        "title": "[TEST] TP IoT",
        "start_datetime": (now - timedelta(minutes=30)).isoformat() + "Z",
        "end_datetime":   (now + timedelta(minutes=45)).isoformat() + "Z",
        "people_count": 10
    },
    # B201 : résa dans 90 min → ATTENTE (pas encore besoin de chauffer)
    {
        "room_id": 3,
        "user_name": "Test User",
        "title": "[TEST] Reunion DevOps",
        "start_datetime": (now + timedelta(minutes=90)).isoformat() + "Z",
        "end_datetime":   (now + timedelta(minutes=150)).isoformat() + "Z",
        "people_count": 6
    },
    # Amphi : résa en cours + surchauffe (31°C)
    {
        "room_id": 4,
        "user_name": "Test User",
        "title": "[TEST] Conférence",
        "start_datetime": (now - timedelta(minutes=10)).isoformat() + "Z",
        "end_datetime":   (now + timedelta(minutes=110)).isoformat() + "Z",
        "people_count": 80
    },
]

for r in reservations:
    conn.execute("""
        INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (r["room_id"], r["user_name"], r["title"],
          r["start_datetime"], r["end_datetime"], r["people_count"]))

conn.commit()
conn.close()

print("✅ Réservations de test insérées dans rate.db")
print()
print("Résultats attendus :")
print("  A101 (16°C) + résa dans 20 min  → 🟠 PRECHAUFFAGE  / HEAT_ON")
print("  A102 (22°C) + résa en cours     → 🟢 CIBLE_ATTEINTE / HEAT_OFF")
print("  B201 (14°C) + résa dans 90 min  → 🟡 ATTENTE        / WAIT")
print("  Amphi(31°C) + résa en cours     → 🟢 CIBLE_ATTEINTE / HEAT_OFF  (ou surchauffe si implémenté)")