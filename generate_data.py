import json, random, sqlite3
from datetime import datetime, timedelta
from weather import get_weather

DB_FILE  = "rate.db"
OUT_FILE = "measures.ndjson"

ROOMS = {
    1: {"name": "A101",  "capacity": 30,  "base_temp": 16.0},
    2: {"name": "A102",  "capacity": 20,  "base_temp": 15.5},
    3: {"name": "B201",  "capacity": 15,  "base_temp": 17.0},
    4: {"name": "Amphi", "capacity": 100, "base_temp": 14.0},
}

def get_reservations():
    c    = sqlite3.connect(DB_FILE)
    rows = c.execute(
        "SELECT room_id, start_datetime, end_datetime, people_count FROM reservations"
    ).fetchall()
    c.close()
    return rows

def get_res_info(room_id, dt, reservations):
    is_occupied      = 0
    people_count     = 0
    res_duration_min = 0
    minutes_to_start = 999

    for r in reservations:
        if r[0] != room_id: continue
        start = datetime.fromisoformat(r[1])
        end   = datetime.fromisoformat(r[2])

        if start <= dt <= end:
            is_occupied      = 1
            people_count     = r[3]
            res_duration_min = int((end - start).total_seconds() / 60)

        elif dt < start:
            diff = int((start - dt).total_seconds() / 60)
            if diff < minutes_to_start:
                minutes_to_start = diff
                people_count     = r[3]

    return is_occupied, people_count, res_duration_min, minutes_to_start

# Météo simulée sur 7 jours (varier légèrement chaque jour)
def sim_weather(dt):
    h = dt.hour
    base_outdoor = 8.0 + random.uniform(-2, 2)
    return {
        "outdoor_temp": round(base_outdoor + (-3 if h < 6 or h > 21 else 0) + random.uniform(-1, 1), 2),
        "outdoor_hum":  round(random.uniform(55, 85), 2),
        "wind_speed":   round(random.uniform(0, 25), 1),
        "weather_code": random.choice([0, 1, 2, 3, 61, 71])
    }

START        = datetime.utcnow() - timedelta(days=7)
INTERVAL     = timedelta(minutes=5)
reservations = get_reservations()
measures     = []
current_time = START

while current_time < datetime.utcnow():
    h          = current_time.hour
    weekday    = current_time.weekday()
    is_weekend = 1 if weekday >= 5 else 0
    weather    = sim_weather(current_time)

    for room_id, info in ROOMS.items():
        base         = info["base_temp"]
        night_factor = -2.0 if (h < 7 or h > 20) else 0.0

        is_occ, people, duration, mins_to_start = get_res_info(
            room_id, current_time, reservations
        )

        heat_factor = (people / info["capacity"]) * 2.5 if is_occ else 0
        temp = round(base + night_factor + heat_factor + random.uniform(-0.3, 0.3), 2)
        co2  = round(400 + (people * 15) + random.uniform(-20, 20), 1) if is_occ \
               else round(random.uniform(400, 600), 1)

        measures.append(json.dumps({
            "room_id":          room_id,
            "sensor_id":        f"rpi5-room-{room_id}",
            "temp":             temp,
            "hum":              round(random.uniform(40, 65), 2),
            "co2":              co2,
            "motion":           bool(is_occ),
            "hour":             h,
            "weekday":          weekday,
            "is_weekend":       is_weekend,
            "people_count":     people,
            "room_capacity":    info["capacity"],
            "occupancy_rate":   round(people / info["capacity"], 2),
            "minutes_to_start": mins_to_start,
            "is_occupied":      is_occ,
            "res_duration_min": duration,
            **weather,
            "timestamp":        current_time.isoformat() + "Z"
        }))

    current_time += INTERVAL

with open(OUT_FILE, "w") as f:
    f.write("\n".join(measures) + "\n")

print(f"✅ {len(measures)} mesures générées ({len(measures)//len(ROOMS)} par salle)")
