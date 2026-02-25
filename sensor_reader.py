import json, time, random
from datetime import datetime

# ── Pins ──────────────────────────────────────────────
# PIR : GND=6  OUT=8(GPIO14)  VCC=17
# SCD41 : GND=14  VDD=1  SCL=5(GPIO3)  SDA=3(GPIO2)

PIR_PIN  = 14
ROOM_ID  = 1
INTERVAL = 10
DB_FILE  = "measures.ndjson"

# ── Init ──────────────────────────────────────────────
try:
    import board, busio
    import RPi.GPIO as GPIO
    import adafruit_scd4x

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)

    i2c    = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_scd4x.SCD4X(i2c)
    sensor.start_periodic_measurement()

    SIMULATION = False
    print("✅ SCD41 + PIR GPIO14 OK")
    time.sleep(5)  # SCD41 a besoin de 5s pour la première mesure

except Exception as e:
    SIMULATION = True
    print(f"⚠️  Mode simulation ({e})")

# ── Lecture ───────────────────────────────────────────
def read():
    if SIMULATION:
        h    = datetime.now().hour
        base = 17.0 + (-2.0 if h < 7 or h > 20 else 0.0)
        return {
            "temp":   round(base + random.uniform(-0.3, 0.3), 2),
            "hum":    round(random.uniform(40, 65), 2),
            "co2":    round(random.uniform(400, 1200), 1),
            "motion": False
        }

    # SCD41 : données dispo uniquement quand data_ready = True
    while not sensor.data_ready:
        time.sleep(0.5)

    return {
        "temp":   round(sensor.temperature, 2),
        "hum":    round(sensor.relative_humidity, 2),
        "co2":    round(sensor.CO2, 1),
        "motion": bool(GPIO.input(PIR_PIN))
    }

# ── Boucle ────────────────────────────────────────────
print(f"🌡️  Lecture toutes les {INTERVAL}s\n")

while True:
    data    = read()
    measure = {
        "room_id":   ROOM_ID,
        "sensor_id": "rpi5-room-1",
        **data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    with open(DB_FILE, "a") as f:
        f.write(json.dumps(measure) + "\n")

    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"T:{data['temp']}°C  "
          f"H:{data['hum']}%  "
          f"CO2:{data['co2']}ppm  "
          f"PIR:{'OUI' if data['motion'] else 'non'}")

    time.sleep(INTERVAL)
