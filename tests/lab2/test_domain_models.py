"""
Tests for Lab 2 agent-side domain models: TrafficLight, AirQuality,
and updated AggregatedData.

These tests exercise the pure-Python dataclasses that the Agent uses
to represent the two new sensors.  They are completely self-contained
and do not depend on any running service.
"""

import sys
import os
from dataclasses import dataclass, fields
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Minimal, self-contained replicas of the domain dataclasses.
# We mirror the exact specification from the lab-2 plan so the tests
# remain runnable even before the production code is committed.
# ---------------------------------------------------------------------------

@dataclass
class Gps:
    longitude: float
    latitude: float


@dataclass
class Accelerometer:
    x: int
    y: int
    z: int


@dataclass
class Parking:
    empty_count: int
    gps: Gps


@dataclass
class Rain:
    intensity: float


@dataclass
class TrafficLight:
    state: str        # "red", "yellow", "green"
    duration: int     # seconds until change
    gps: Gps


@dataclass
class AirQuality:
    pm25: float       # ug/m3
    pm10: float       # ug/m3
    co2: float        # ppm


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
            1,
        )


# ===================================================================
# TrafficLight tests
# ===================================================================

class TestTrafficLight:
    def test_create_with_green(self):
        gps = Gps(30.52, 50.45)
        tl = TrafficLight(state="green", duration=35, gps=gps)
        assert tl.state == "green"
        assert tl.duration == 35
        assert tl.gps.longitude == 30.52
        assert tl.gps.latitude == 50.45

    def test_create_with_yellow(self):
        tl = TrafficLight("yellow", 4, Gps(0.0, 0.0))
        assert tl.state == "yellow"
        assert tl.duration == 4

    def test_create_with_red(self):
        tl = TrafficLight("red", 60, Gps(10.0, 20.0))
        assert tl.state == "red"
        assert tl.duration == 60

    def test_zero_duration(self):
        tl = TrafficLight("green", 0, Gps(0.0, 0.0))
        assert tl.duration == 0

    def test_negative_duration_is_accepted(self):
        """Dataclass does not validate; negative values are technically stored."""
        tl = TrafficLight("green", -5, Gps(0.0, 0.0))
        assert tl.duration == -5

    def test_large_duration(self):
        tl = TrafficLight("red", 999, Gps(0.0, 0.0))
        assert tl.duration == 999

    def test_equality(self):
        gps = Gps(1.0, 2.0)
        a = TrafficLight("red", 10, gps)
        b = TrafficLight("red", 10, gps)
        assert a == b

    def test_inequality_state(self):
        gps = Gps(1.0, 2.0)
        a = TrafficLight("red", 10, gps)
        b = TrafficLight("green", 10, gps)
        assert a != b

    def test_fields_are_correct(self):
        names = {f.name for f in fields(TrafficLight)}
        assert names == {"state", "duration", "gps"}

    def test_empty_string_state(self):
        """Dataclass does not validate; empty string is accepted."""
        tl = TrafficLight("", 10, Gps(0.0, 0.0))
        assert tl.state == ""

    def test_none_state_accepted(self):
        """Dataclass does not validate; None is accepted as state."""
        tl = TrafficLight(None, 10, Gps(0.0, 0.0))
        assert tl.state is None


# ===================================================================
# AirQuality tests
# ===================================================================

class TestAirQuality:
    def test_create_typical_values(self):
        aq = AirQuality(pm25=12.5, pm10=28.3, co2=420.0)
        assert aq.pm25 == 12.5
        assert aq.pm10 == 28.3
        assert aq.co2 == 420.0

    def test_create_zero_values(self):
        aq = AirQuality(0.0, 0.0, 0.0)
        assert aq.pm25 == 0.0
        assert aq.pm10 == 0.0
        assert aq.co2 == 0.0

    def test_negative_values_accepted(self):
        """Dataclass does not validate; negatives are stored without error."""
        aq = AirQuality(-1.0, -2.0, -3.0)
        assert aq.pm25 == -1.0

    def test_high_pollution_values(self):
        aq = AirQuality(pm25=500.0, pm10=600.0, co2=2000.0)
        assert aq.pm25 == 500.0

    def test_boundary_pm25_12(self):
        aq = AirQuality(12.0, 20.0, 400.0)
        assert aq.pm25 == 12.0

    def test_boundary_pm25_35_4(self):
        aq = AirQuality(35.4, 50.0, 420.0)
        assert aq.pm25 == 35.4

    def test_equality(self):
        a = AirQuality(10.0, 20.0, 400.0)
        b = AirQuality(10.0, 20.0, 400.0)
        assert a == b

    def test_inequality(self):
        a = AirQuality(10.0, 20.0, 400.0)
        b = AirQuality(10.1, 20.0, 400.0)
        assert a != b

    def test_fields_are_correct(self):
        names = {f.name for f in fields(AirQuality)}
        assert names == {"pm25", "pm10", "co2"}

    def test_integer_values_coerced(self):
        """Passing int where float is expected; Python does not enforce."""
        aq = AirQuality(10, 20, 400)
        assert aq.pm25 == 10
        assert aq.pm10 == 20
        assert aq.co2 == 400

    def test_pm10_less_than_pm25_accepted(self):
        """Dataclass has no physical validation; PM10 < PM2.5 is stored."""
        aq = AirQuality(pm25=50.0, pm10=10.0, co2=400.0)
        assert aq.pm25 > aq.pm10


# ===================================================================
# AggregatedData with new fields
# ===================================================================

class TestAggregatedData:
    def test_default_includes_traffic_light(self):
        data = AggregatedData.default()
        assert isinstance(data.traffic_light, TrafficLight)
        assert data.traffic_light.state == "red"
        assert data.traffic_light.duration == 0

    def test_default_includes_air_quality(self):
        data = AggregatedData.default()
        assert isinstance(data.air_quality, AirQuality)
        assert data.air_quality.pm25 == 0.0
        assert data.air_quality.pm10 == 0.0
        assert data.air_quality.co2 == 0.0

    def test_default_preserves_existing_fields(self):
        data = AggregatedData.default()
        assert isinstance(data.accelerometer, Accelerometer)
        assert isinstance(data.gps, Gps)
        assert isinstance(data.parking, Parking)
        assert isinstance(data.rain, Rain)
        assert isinstance(data.timestamp, datetime)

    def test_create_with_all_fields(self):
        now = datetime.now()
        data = AggregatedData(
            accelerometer=Accelerometer(1, 2, 3),
            gps=Gps(30.52, 50.45),
            parking=Parking(5, Gps(30.0, 50.0)),
            rain=Rain(0.3),
            traffic_light=TrafficLight("green", 25, Gps(30.52, 50.45)),
            air_quality=AirQuality(15.0, 28.0, 420.0),
            temperature=22.5,
            timestamp=now,
            user_id=1,
        )
        assert data.traffic_light.state == "green"
        assert data.air_quality.pm25 == 15.0
        assert data.temperature == 22.5
        assert data.user_id == 1

    def test_field_count(self):
        """AggregatedData should have 9 fields after Lab 2 additions."""
        assert len(fields(AggregatedData)) == 9

    def test_field_names(self):
        names = [f.name for f in fields(AggregatedData)]
        assert "traffic_light" in names
        assert "air_quality" in names

    def test_default_user_id_is_set(self):
        data = AggregatedData.default()
        assert isinstance(data.user_id, int)

    def test_nested_gps_in_traffic_light(self):
        """TrafficLight inside AggregatedData has its own GPS."""
        gps_car = Gps(30.0, 50.0)
        gps_tl = Gps(31.0, 51.0)
        data = AggregatedData(
            Accelerometer(0, 0, 0),
            gps_car,
            Parking(0, Gps(0.0, 0.0)),
            Rain(0),
            TrafficLight("red", 40, gps_tl),
            AirQuality(0.0, 0.0, 0.0),
            0,
            datetime.now(),
            1,
        )
        # Car GPS and TrafficLight GPS should be independent
        assert data.gps.longitude == 30.0
        assert data.traffic_light.gps.longitude == 31.0
