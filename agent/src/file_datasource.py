from csv import DictReader
from datetime import datetime
from domain.accelerometer import Accelerometer
from domain.gps import Gps
from domain.aggregated_data import AggregatedData
from domain.parking import Parking
from domain.rain import Rain
from domain.traffic_light import TrafficLight
from domain.air_quality import AirQuality
import config


class FileDatasource:
    def __init__(
        self,
        accelerometer_filename: str,
        gps_filename: str,
        parking_filename: str,
        rain_filename: str,
        temp_filename: str,
        traffic_light_filename: str,
        air_quality_filename: str,
    ) -> None:
        self.accelerometer_filename = accelerometer_filename
        self.gps_filename = gps_filename
        self.parking_filename = parking_filename
        self.rain_filename = rain_filename
        self.temp_filename = temp_filename
        self.traffic_light_filename = traffic_light_filename
        self.air_quality_filename = air_quality_filename
        self.accel_file = None
        self.gps_file = None
        self.parking_file = None
        self.rain_file = None
        self.temp_file = None
        self.traffic_light_file = None
        self.air_quality_file = None
        self.agr_data = None

    def read(self) -> AggregatedData:
        try:
            data = self.agr_data.pop(0)
            data.timestamp = datetime.now()
            return data
        except IndexError:
            return AggregatedData.default()

    def startReading(self):
        self.accel_file = open(self.accelerometer_filename, "r")
        self.gps_file = open(self.gps_filename, "r")
        self.parking_file = open(self.parking_filename, "r")
        self.rain_file = open(self.rain_filename, "r")
        self.temp_file = open(self.temp_filename, "r")
        self.traffic_light_file = open(self.traffic_light_filename, "r")
        self.air_quality_file = open(self.air_quality_filename, "r")

        accel_reader = DictReader(self.accel_file, delimiter=",")
        gps_reader = DictReader(self.gps_file, delimiter=",")
        parking_reader = DictReader(self.parking_file, delimiter=",")
        rain_reader = DictReader(self.rain_file, delimiter=",")
        temp_header = DictReader(self.temp_file, delimiter=",")
        traffic_light_reader = DictReader(self.traffic_light_file, delimiter=",")
        air_quality_reader = DictReader(self.air_quality_file, delimiter=",")


        accel_data = [
            Accelerometer(int(row["x"]), int(row["y"]), int(row["z"]))
            for row in accel_reader
        ]

        gps_data = [
            Gps(float(row["latitude"]), float(row["longitude"]))
            for row in gps_reader
        ]

        parking_data = [
            Parking(int(row["empty_count"]), Gps(float(row["latitude"]), float(row["longitude"])))
            for row in parking_reader
        ]

        rain_data = [
            Rain(float(row["intensity"]))
            for row in rain_reader
        ]

        temp_data = [
            float(row["temperature"])
            for row in temp_header
        ]

        traffic_light_data = [
            TrafficLight(
                row["state"],
                int(row["duration"]),
                Gps(float(row["latitude"]), float(row["longitude"]))
            )
            for row in traffic_light_reader
        ]

        air_quality_data = [
            AirQuality(float(row["pm25"]), float(row["pm10"]), float(row["co2"]))
            for row in air_quality_reader
        ]

        self.agr_data = [
            AggregatedData(
                accel,
                gps if gps is not None else Gps(0.0, 0.0),
                parking if parking is not None else Parking(0, Gps(0.0, 0.0)),
                rain if rain is not None else Rain(0),
                traffic_light if traffic_light is not None else TrafficLight("red", 0, Gps(0.0, 0.0)),
                air_quality if air_quality is not None else AirQuality(0.0, 0.0, 0.0),
                temp,
                datetime.now(),
                config.USER_ID,
            )
            for accel, gps, parking, rain, traffic_light, air_quality, temp in zip(
                accel_data,
                gps_data + [None] * (len(accel_data) - len(gps_data)),
                parking_data + [None] * (len(accel_data) - len(parking_data)),
                rain_data + [None] * (len(accel_data) - len(rain_data)),
                traffic_light_data + [None] * (len(accel_data) - len(traffic_light_data)),
                air_quality_data + [None] * (len(accel_data) - len(air_quality_data)),
                temp_data + [None] * (len(accel_data) - len(temp_data)),
            )
        ]
        print("Successfully opened files")

    def stopReading(self):
        if self.accel_file:
            print("Closing file...", self.accel_file.name)
            self.accel_file.close()
        if self.gps_file:
            print("Closing file...", self.gps_file.name)
            self.gps_file.close()
        if self.parking_file:
            print("Closing file...", self.parking_file.name)
            self.parking_file.close()
        if self.rain_file:
            print("Closing file...", self.rain_file.name)
            self.rain_file.close()
        if self.temp_file:
            print("Closing file...", self.temp_file.name)
            self.temp_file.close()
        if self.traffic_light_file:
            print("Closing file...", self.traffic_light_file.name)
            self.traffic_light_file.close()
        if self.air_quality_file:
            print("Closing file...", self.air_quality_file.name)
            self.air_quality_file.close()
