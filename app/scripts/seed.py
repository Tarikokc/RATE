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

now = now_local()

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