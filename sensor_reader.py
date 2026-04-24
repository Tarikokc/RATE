import json, time, random, requests
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from backend.time_helper import now_local

# ── Config ────────────────────────────────────────────
PIR_PIN   = 14
ROOM_ID   = 1
SENSOR_ID = "rpi5-room-1"
INTERVAL  = 10
FLASK_URL = os.getenv("API_URL", "http://localhost:5000") + "/api/measures"

# ── Init capteurs ─────────────────────────────────────
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
    time.sleep(5)

except Exception as e:
    SIMULATION = True
    print(f"⚠️  Mode simulation ({e})")

# ── Lecture capteur ───────────────────────────────────
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

    while not sensor.data_ready:
        time.sleep(0.5)

    return {
        "temp":   round(sensor.temp, 2),
        "hum":    round(sensor.relative_humidity, 2),
        "co2":    round(sensor.CO2, 1),
        "motion": bool(GPIO.input(PIR_PIN))
    }

# ── Boucle ────────────────────────────────────────────
print(f"🌡️  Envoi toutes les {INTERVAL}s → {FLASK_URL}\n")

while True:
    data    = read()
    payload = {
        "sensor_id": SENSOR_ID,
        "room_id":   ROOM_ID,
        **data
    }

    try:
        r = requests.post(FLASK_URL, json=payload, timeout=5)
        status = r.status_code
    except Exception as e:
        status = f"ERR ({e})"

    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"T:{data['temp']}°C  "
          f"H:{data['hum']}%  "
          f"CO2:{data['co2']}ppm  "
          f"PIR:{'OUI' if data['motion'] else 'non'}  "
          f"→ HTTP {status}")

    time.sleep(INTERVAL)
