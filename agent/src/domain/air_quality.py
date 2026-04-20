from dataclasses import dataclass


@dataclass
class AirQuality:
    pm25: float   # mcg/m3
    pm10: float   # mcg/m3
    co2: float    # ppm
