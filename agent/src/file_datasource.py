from csv import DictReader
from datetime import datetime
from domain.accelerometer import Accelerometer
from domain.gps import Gps
from domain.aggregated_data import AggregatedData
from domain.parking import Parking
from domain.rain import Rain
import config


class FileDatasource:
    def __init__(
        self,
        accelerometer_filename: str,
        gps_filename: str,
        parking_filename: str,
        rain_filename: str,
        temp_filename: str,
    ) -> None:
        self.accelerometer_filename = accelerometer_filename
        self.gps_filename = gps_filename
        self.parking_filename = parking_filename
        self.rain_filename = rain_filename
        self.temp_filename = temp_filename
        self.accel_file = None
        self.gps_file = None
        self.parking_file = None
        self.rain_file = None
        self.temp_file = None
        self.agr_data = None

    def read(self) -> AggregatedData:
        try:
            return self.agr_data.pop(0)
        except IndexError:
            return AggregatedData.default()

    def startReading(self):
        self.accel_file = open(self.accelerometer_filename, "r")
        self.gps_file = open(self.gps_filename, "r")
        self.parking_file = open(self.parking_filename, "r")
        self.rain_file = open(self.rain_filename, "r")
        self.temp_file = open(self.temp_filename, "r")

        accel_reader = DictReader(self.accel_file, delimiter=",")
        gps_reader = DictReader(self.gps_file, delimiter=",")
        parking_reader = DictReader(self.parking_file, delimiter=",")
        rain_reader = DictReader(self.rain_file, delimiter=",")
        temp_header = DictReader(self.temp_file, delimiter=",")


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

        self.agr_data = [
            AggregatedData(
                accel,
                gps if gps is not None else Gps(0.0, 0.0),
                parking if parking is not None else Parking(0, Gps(0.0, 0.0)),
                rain if rain is not None else Rain(0),
                temp,
                datetime.now(),
                config.USER_ID,
            )
            for accel, gps, parking, rain, temp in zip(
                accel_data,
                gps_data + [None] * (len(accel_data) - len(gps_data)),
                parking_data + [None] * (len(accel_data) - len(parking_data)),
                rain_data + [None] * (len(accel_data) - len(rain_data)),
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
            print("Closing file...", self.rain_file.name)
            self.temp_file.close()
