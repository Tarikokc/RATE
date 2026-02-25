import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import datetime

# Coordonnées — changer selon ta ville
LATITUDE  = 48.8566   # Paris
LONGITUDE = 2.3522

cache_session  = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session  = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo      = openmeteo_requests.Client(session=retry_session)

_cache = {"data": None, "ts": None}

def get_weather() -> dict:
    """Retourne la météo actuelle. Cache interne 10 min."""
    now = datetime.utcnow()

    if _cache["data"] and _cache["ts"]:
        if (now - _cache["ts"]).total_seconds() < 600:
            return _cache["data"]

    try:
        responses = openmeteo.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  LATITUDE,
                "longitude": LONGITUDE,
                "current":   ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
                "forecast_days": 1
            }
        )

        current = responses[0].Current()
        data = {
            "outdoor_temp": round(current.Variables(0).Value(), 2),
            "outdoor_hum":  round(current.Variables(1).Value(), 2),
            "wind_speed":   round(current.Variables(2).Value(), 2),
        }

    except Exception as e:
        print(f"⚠️  Météo indisponible ({e}) → valeurs par défaut")
        data = {
            "outdoor_temp": 10.0,
            "outdoor_hum":  60.0,
            "wind_speed":   5.0,
        }

    _cache["data"] = data
    _cache["ts"]   = now
    return data
