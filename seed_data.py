import json, sqlite3, os, random
from datetime import datetime, timedelta

DATA_FILE = "measures.ndjson"
DB_FILE   = "rate.db"

# ─── Config ───────────────────────────────────────────
ROOMS = [
    {"id": 1, "sensor_id": "rpi5-room-1", "base_temp": 19.5},
    {"id": 2, "sensor_id": "rpi5-room-2", "base_temp": 21.2},
    {"id": 3, "sensor_id": "rpi5-room-3", "base_temp": 17.8},
    {"id": 4, "sensor_id": "rpi5-room-4", "base_temp": 22.4},
]

now = datetime.utcnow()

# ─── 1. Mesures (48h d'historique, 1 toutes les 5 min) ───
print("📊 Génération des mesures...")

# Vide l'ancien fichier
with open(DATA_FILE, "w", encoding="utf-8") as f:
    pass

measures = []
for i in range(576):  # 48h × 12 mesures/h
    ts = now - timedelta(minutes=5 * (576 - i))
    hour = ts.hour

    # Température varie selon l'heure (plus froid la nuit)
    temp_factor = 1.0 if 8 <= hour <= 18 else 0.7

    for room in ROOMS:
        temp  = round(room["base_temp"] * temp_factor + random.uniform(-0.5, 0.5), 2)
        hum   = round(random.uniform(40, 65), 1)
        co2   = int(random.uniform(400, 900) if (8 <= hour <= 18) else random.uniform(380, 450))
        motion = (8 <= hour <= 18) and random.random() > 0.4

        measures.append({
            "room_id":   room["id"],
            "sensor_id": room["sensor_id"],
            "temp":      temp,
            "hum":       hum,
            "co2":       co2,
            "motion":    motion,
            "timestamp": ts.isoformat() + "Z"
        })

with open(DATA_FILE, "a", encoding="utf-8") as f:
    for m in measures:
        f.write(json.dumps(m) + "\n")

print(f"  ✅ {len(measures)} mesures insérées ({len(measures)//len(ROOMS)} par salle)")


# ─── 2. Réservations fictives ──────────────────────────
print("📅 Génération des réservations...")

conn = sqlite3.connect(DB_FILE)
conn.execute("DELETE FROM reservations WHERE user_name LIKE 'Demo%'")

users   = ["Demo Alice", "Demo Bob", "Demo Tarik", "Demo Sarah", "Demo Marc"]
titles  = ["Cours Angular", "TP IoT", "Réunion DevOps", "Conférence IA", "TD Python", "Réunion projet", "Formation Docker"]

reservations = []

for day_offset in range(-2, 5):  # 2 jours passés + aujourd'hui + 4 jours futurs
    day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)

    # Créneaux horaires typiques
    slots = [8, 10, 14, 16]

    for room in ROOMS:
        for slot in slots:
            if random.random() < 0.55:  # 55% de chances qu'un créneau soit pris
                duration = random.choice([60, 90, 120])
                start    = day + timedelta(hours=slot)
                end      = start + timedelta(minutes=duration)

                reservations.append((
                    room["id"],
                    random.choice(users),
                    random.choice(titles),
                    start.isoformat() + "Z",
                    end.isoformat()   + "Z",
                    random.randint(3, min(20, room["id"] * 8))
                ))

# Réservations spéciales pour tester les états de chauffage NOW
special = [
    # A101 : résa en cours → EN_CHAUFFE (temp basse)
    (1, "Demo Test", "[DEMO] Cours en cours",
     (now - timedelta(minutes=15)).isoformat() + "Z",
     (now + timedelta(minutes=45)).isoformat() + "Z", 10),

    # A102 : résa dans 25 min → PRECHAUFFAGE
    (2, "Demo Test", "[DEMO] Réunion imminente",
     (now + timedelta(minutes=25)).isoformat() + "Z",
     (now + timedelta(minutes=85)).isoformat() + "Z", 8),

    # B201 : résa dans 3h → ATTENTE
    (3, "Demo Test", "[DEMO] Formation après-midi",
     (now + timedelta(hours=3)).isoformat() + "Z",
     (now + timedelta(hours=5)).isoformat() + "Z", 5),

    # Amphi : aucune résa → STANDBY
]

for r in reservations + special:
    try:
        conn.execute("""
            INSERT INTO reservations (room_id, user_name, title, start_datetime, end_datetime, people_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, r)
    except Exception as e:
        print(f"  ⚠️ Skipped: {e}")

conn.commit()
conn.close()

print(f"  ✅ {len(reservations) + len(special)} réservations insérées")

print()
print("États de chauffage attendus maintenant :")
print("  Salle A101 → 🟠 EN_CHAUFFE     (résa en cours, temp ~17°C)")
print("  Salle A102 → 🟠 PRÉCHAUFFAGE   (résa dans 25 min)")
print("  Salle B201 → 🟡 ATTENTE        (résa dans 3h)")
print("  Amphi      → ⚫ STANDBY        (aucune résa active)")
print()
print("✅ Done — relance Flask pour voir les changements")