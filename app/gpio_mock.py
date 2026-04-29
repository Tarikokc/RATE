# Remplace RPi.GPIO sur PC/Mac — drop-in, aucune modif du reste du code
import logging

log = logging.getLogger("GPIO_MOCK")

_state: dict[int, bool] = {}

BCM = OUT = IN = 0

def setmode(mode): pass

def setup(pin, mode):
    _state.setdefault(pin, False)

def output(pin, val: bool):
    _state[pin] = bool(val)
    log.info(f"  🔌 Pin {pin:>2} → {'HIGH ■  (ON) ' if val else 'LOW  □  (OFF)'}")

def input(pin) -> bool:
    return _state.get(pin, False)

def get_all_states() -> dict[int, bool]:
    return dict(_state)

def cleanup():
    _state.clear()
