from dataclasses import dataclass
from domain.gps import Gps

@dataclass
class TrafficLight:
    state: str        # "red", "yellow", "green"
    duration: int     # seconds until change
    gps: Gps          # traffic light coordinates
