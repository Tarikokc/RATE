import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "dev")
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

    API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")

    DB_PATH = os.getenv("DB_PATH", "data/rate.db")

    TARGET_TEMP = float(os.getenv("TARGET_TEMP", "20.0"))
    HEAT_ADVANCE_MIN = int(os.getenv("HEAT_ADVANCE_MIN", "60"))
    DEG_PER_HOUR = float(os.getenv("DEG_PER_HOUR", "2.5"))
    TEMP_TOLERANCE = float(os.getenv("TEMP_TOLERANCE", "0.5"))

    WEATHER_LATITUDE = float(os.getenv("WEATHER_LATITUDE", "48.8566"))
    WEATHER_LONGITUDE = float(os.getenv("WEATHER_LONGITUDE", "2.3522"))