from datetime import datetime
import pytz

TZ = pytz.timezone("Europe/Paris")

def now_local() -> datetime:
    """Retourne l'heure actuelle en heure locale française (naive datetime)."""
    return datetime.now(TZ).replace(tzinfo=None)

def to_local(dt: datetime) -> datetime:
    """Convertit un datetime UTC naive en heure locale française."""
    return pytz.utc.localize(dt).astimezone(TZ).replace(tzinfo=None)
