"""
Shared fixtures for Lab 2 and Lab 3 tests.

All fixtures are self-contained and do not require Docker or external services.
"""

import pytest
from datetime import datetime


# ──────────────────────────────────────────────
# Agent-side dataclass fixtures (plain Python)
# ──────────────────────────────────────────────

class _Gps:
    """Lightweight stand-in for agent domain Gps dataclass."""
    def __init__(self, longitude: float = 0.0, latitude: float = 0.0):
        self.longitude = longitude
        self.latitude = latitude

    def __eq__(self, other):
        return (isinstance(other, _Gps)
                and self.longitude == other.longitude
                and self.latitude == other.latitude)


class _Accelerometer:
    def __init__(self, x: int = 0, y: int = 0, z: int = 0):
        self.x = x
        self.y = y
        self.z = z


class _Parking:
    def __init__(self, empty_count: int = 0, gps=None):
        self.empty_count = empty_count
        self.gps = gps or _Gps()


class _Rain:
    def __init__(self, intensity: float = 0.0):
        self.intensity = intensity


class _TrafficLight:
    def __init__(self, state: str = "red", duration: int = 0, gps=None):
        self.state = state
        self.duration = duration
        self.gps = gps or _Gps()


class _AirQuality:
    def __init__(self, pm25: float = 0.0, pm10: float = 0.0, co2: float = 0.0):
        self.pm25 = pm25
        self.pm10 = pm10
        self.co2 = co2


@pytest.fixture
def sample_gps():
    return _Gps(longitude=30.52, latitude=50.45)


@pytest.fixture
def sample_traffic_light(sample_gps):
    return _TrafficLight(state="green", duration=35, gps=sample_gps)


@pytest.fixture
def sample_air_quality():
    return _AirQuality(pm25=12.5, pm10=28.3, co2=420.0)


@pytest.fixture
def sample_accelerometer():
    return _Accelerometer(x=1, y=2, z=3)


@pytest.fixture
def sample_rain():
    return _Rain(intensity=0.5)


@pytest.fixture
def sample_parking(sample_gps):
    return _Parking(empty_count=5, gps=sample_gps)


# ──────────────────────────────────────────────
# Edge / Hub Pydantic model fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def gps_data_dict():
    return {"latitude": 50.45, "longitude": 30.52}


@pytest.fixture
def accelerometer_data_dict():
    return {"x": 0.1, "y": 0.2, "z": 0.3}


@pytest.fixture
def rain_data_dict():
    return {"intensity": 0.5}


@pytest.fixture
def traffic_light_data_dict(gps_data_dict):
    return {
        "state": "green",
        "duration": 35,
        "gps": gps_data_dict,
    }


@pytest.fixture
def air_quality_data_dict():
    return {
        "pm25": 12.5,
        "pm10": 28.3,
        "co2": 420.0,
    }


@pytest.fixture
def agent_data_dict(
    accelerometer_data_dict,
    gps_data_dict,
    rain_data_dict,
    traffic_light_data_dict,
    air_quality_data_dict,
):
    return {
        "user_id": 1,
        "accelerometer": accelerometer_data_dict,
        "gps": gps_data_dict,
        "rain": rain_data_dict,
        "traffic_light": traffic_light_data_dict,
        "air_quality": air_quality_data_dict,
        "temperature": 22.5,
        "timestamp": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def processed_agent_data_dict(agent_data_dict):
    return {
        "road_state": "Even",
        "rain_state": "Shower",
        "traffic_light_state": "Safe to go",
        "air_quality_state": "Moderate",
        "agent_data": agent_data_dict,
    }


# ──────────────────────────────────────────────
# Store flat-row fixture (as would be inserted into DB)
# ──────────────────────────────────────────────

@pytest.fixture
def store_flat_row(processed_agent_data_dict):
    """
    Flattened dict matching the DB columns defined in the Lab 2 plan.
    """
    ad = processed_agent_data_dict["agent_data"]
    return {
        "road_state": processed_agent_data_dict["road_state"],
        "rain_state": processed_agent_data_dict["rain_state"],
        "traffic_light_state": processed_agent_data_dict["traffic_light_state"],
        "air_quality_state": processed_agent_data_dict["air_quality_state"],
        "user_id": ad["user_id"],
        "x": ad["accelerometer"]["x"],
        "y": ad["accelerometer"]["y"],
        "z": ad["accelerometer"]["z"],
        "latitude": ad["gps"]["latitude"],
        "longitude": ad["gps"]["longitude"],
        "rain_intensity": ad["rain"]["intensity"],
        "temperature": ad["temperature"],
        "traffic_light_color": ad["traffic_light"]["state"],
        "traffic_light_duration": ad["traffic_light"]["duration"],
        "traffic_light_latitude": ad["traffic_light"]["gps"]["latitude"],
        "traffic_light_longitude": ad["traffic_light"]["gps"]["longitude"],
        "pm25": ad["air_quality"]["pm25"],
        "pm10": ad["air_quality"]["pm10"],
        "co2": ad["air_quality"]["co2"],
        "timestamp": ad["timestamp"],
    }


# ──────────────────────────────────────────────
# Lab 3 — ML predictor & metrics fixtures
# ──────────────────────────────────────────────

import sys
import os
from unittest.mock import MagicMock
from datetime import timedelta

import numpy as np

# Ensure predictor/ and store/ directories are importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _subdir in ("predictor", "store"):
    _path = os.path.join(_PROJECT_ROOT, _subdir)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture
def linear_data():
    """50-point linear time-series: value = 2*i + 10."""
    base = datetime(2026, 1, 1)
    return [
        (base + timedelta(minutes=i), 2.0 * i + 10.0)
        for i in range(50)
    ]


@pytest.fixture
def constant_data():
    """30-point constant time-series: value = 42.0."""
    base = datetime(2026, 1, 1)
    return [
        (base + timedelta(minutes=i), 42.0)
        for i in range(30)
    ]


@pytest.fixture
def small_data():
    """Fewer than 10 data points (5 points)."""
    base = datetime(2026, 1, 1)
    return [
        (base + timedelta(minutes=i), float(i))
        for i in range(5)
    ]


@pytest.fixture
def trending_data():
    """100-point noisy trending data: value = 0.5*i + noise."""
    rng = np.random.RandomState(42)
    base = datetime(2026, 1, 1)
    return [
        (base + timedelta(minutes=i), 0.5 * i + rng.normal(0, 1))
        for i in range(100)
    ]


@pytest.fixture
def mock_db_engine():
    """MagicMock SQLAlchemy engine + connection (context-manager aware)."""
    engine = MagicMock()
    connection = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=connection)
    ctx.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = ctx
    return engine, connection


@pytest.fixture
def sample_db_summary_row():
    """Mock row for /metrics/summary response."""
    row = MagicMock()
    row._mapping = {
        "total_records": 150,
        "avg_temp": 22.5,
        "avg_rain": 3.1,
        "avg_pm25": 18.7,
        "potholes": 12,
        "bumps": 8,
        "first_record": datetime(2026, 1, 1, 0, 0),
        "last_record": datetime(2026, 1, 1, 2, 30),
    }
    return row


@pytest.fixture
def sample_timeseries_rows():
    """Mock rows for /metrics/timeseries response."""
    rows = []
    base = datetime(2026, 1, 1)
    for i in range(5):
        row = MagicMock()
        row._mapping = {
            "timestamp": base + timedelta(minutes=i),
            "temperature": 20.0 + i * 0.5,
        }
        rows.append(row)
    return rows
