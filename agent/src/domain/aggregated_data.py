from dataclasses import dataclass

from datetime import datetime
from domain.accelerometer import Accelerometer
from domain.gps import Gps
from domain.parking import Parking
from domain.rain import Rain
from domain.traffic_light import TrafficLight
from domain.air_quality import AirQuality
import config


@dataclass
class AggregatedData:
    accelerometer: Accelerometer
    gps: Gps
    parking: Parking
    rain: Rain
    traffic_light: TrafficLight
    air_quality: AirQuality
    temperature: float
    timestamp: datetime
    user_id: int

    @staticmethod
    def default():
        return AggregatedData(
            Accelerometer(0, 0, 0),
            Gps(0.0, 0.0),
            Parking(0, Gps(0.0, 0.0)),
            Rain(0),
            TrafficLight("red", 0, Gps(0.0, 0.0)),
            AirQuality(0.0, 0.0, 0.0),
            0,
            datetime.now(),
            config.USER_ID,
        )
