"""
Tests for Lab 2 Pydantic models used by the Edge, Hub, and Store:
TrafficLightData, AirQualityData, updated AgentData, and updated ProcessedAgentData.

All models are self-contained replicas of the planned production code.
"""

import pytest
from datetime import datetime
from pydantic import BaseModel, ValidationError, field_validator


# ---------------------------------------------------------------------------
# Self-contained Pydantic model replicas matching Lab 2 plan.
# ---------------------------------------------------------------------------

class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float


class GpsData(BaseModel):
    latitude: float
    longitude: float


class RainData(BaseModel):
    intensity: float


class TrafficLightData(BaseModel):
    state: str          # "red", "yellow", "green"
    duration: int
    gps: GpsData


class AirQualityData(BaseModel):
    pm25: float
    pm10: float
    co2: float


class AgentData(BaseModel):
    user_id: int
    accelerometer: AccelerometerData
    gps: GpsData
    rain: RainData
    traffic_light: TrafficLightData
    air_quality: AirQualityData
    temperature: float
    timestamp: datetime

    @classmethod
    @field_validator("timestamp", mode="before")
    def parse_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid timestamp format. Expected ISO 8601 format."
            )


class ProcessedAgentData(BaseModel):
    road_state: str
    rain_state: str
    traffic_light_state: str
    air_quality_state: str
    agent_data: AgentData


# ===================================================================
# TrafficLightData
# ===================================================================

class TestTrafficLightData:
    def test_create_valid(self):
        tl = TrafficLightData(
            state="green",
            duration=35,
            gps=GpsData(latitude=50.45, longitude=30.52),
        )
        assert tl.state == "green"
        assert tl.duration == 35
        assert tl.gps.latitude == 50.45

    def test_all_states(self):
        for state in ("red", "yellow", "green"):
            tl = TrafficLightData(
                state=state, duration=10, gps=GpsData(latitude=0, longitude=0)
            )
            assert tl.state == state

    def test_zero_duration(self):
        tl = TrafficLightData(
            state="red", duration=0, gps=GpsData(latitude=0, longitude=0)
        )
        assert tl.duration == 0

    def test_missing_state_raises(self):
        with pytest.raises(ValidationError):
            TrafficLightData(
                duration=10, gps=GpsData(latitude=0, longitude=0)
            )

    def test_missing_gps_raises(self):
        with pytest.raises(ValidationError):
            TrafficLightData(state="red", duration=10)

    def test_missing_duration_raises(self):
        with pytest.raises(ValidationError):
            TrafficLightData(
                state="red", gps=GpsData(latitude=0, longitude=0)
            )

    def test_invalid_duration_type(self):
        with pytest.raises(ValidationError):
            TrafficLightData(
                state="green",
                duration="not_int",
                gps=GpsData(latitude=0, longitude=0),
            )

    def test_nested_gps_dict(self):
        """Pydantic should accept a dict for the nested GpsData."""
        tl = TrafficLightData(
            state="green",
            duration=10,
            gps={"latitude": 50.0, "longitude": 30.0},
        )
        assert isinstance(tl.gps, GpsData)
        assert tl.gps.latitude == 50.0

    def test_model_dump(self):
        tl = TrafficLightData(
            state="yellow",
            duration=4,
            gps=GpsData(latitude=50.0, longitude=30.0),
        )
        d = tl.model_dump()
        assert d == {
            "state": "yellow",
            "duration": 4,
            "gps": {"latitude": 50.0, "longitude": 30.0},
        }

    def test_negative_duration_coerced_to_int(self):
        tl = TrafficLightData(
            state="red", duration=-5, gps=GpsData(latitude=0, longitude=0)
        )
        assert tl.duration == -5

    def test_empty_state_string(self):
        """Pydantic str field accepts empty string."""
        tl = TrafficLightData(
            state="", duration=10, gps=GpsData(latitude=0, longitude=0)
        )
        assert tl.state == ""

    def test_none_gps_raises(self):
        """None is not a valid GpsData."""
        with pytest.raises(ValidationError):
            TrafficLightData(state="green", duration=10, gps=None)


# ===================================================================
# AirQualityData
# ===================================================================

class TestAirQualityData:
    def test_create_valid(self):
        aq = AirQualityData(pm25=12.5, pm10=28.3, co2=420.0)
        assert aq.pm25 == 12.5
        assert aq.pm10 == 28.3
        assert aq.co2 == 420.0

    def test_zero_values(self):
        aq = AirQualityData(pm25=0.0, pm10=0.0, co2=0.0)
        assert aq.pm25 == 0.0

    def test_missing_pm25_raises(self):
        with pytest.raises(ValidationError):
            AirQualityData(pm10=20.0, co2=400.0)

    def test_missing_co2_raises(self):
        with pytest.raises(ValidationError):
            AirQualityData(pm25=10.0, pm10=20.0)

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            AirQualityData(pm25="bad", pm10=20.0, co2=400.0)

    def test_model_dump(self):
        aq = AirQualityData(pm25=35.4, pm10=60.0, co2=450.0)
        d = aq.model_dump()
        assert d == {"pm25": 35.4, "pm10": 60.0, "co2": 450.0}

    def test_high_values(self):
        aq = AirQualityData(pm25=500.0, pm10=800.0, co2=5000.0)
        assert aq.pm25 == 500.0

    def test_int_coerced_to_float(self):
        aq = AirQualityData(pm25=10, pm10=20, co2=400)
        assert isinstance(aq.pm25, float)

    def test_boundary_values(self):
        for val in [12.0, 35.4, 55.4, 150.4, 250.4]:
            aq = AirQualityData(pm25=val, pm10=val * 1.5, co2=400.0)
            assert aq.pm25 == val

    def test_none_value_raises(self):
        """None is not a valid float for pm25."""
        with pytest.raises(ValidationError):
            AirQualityData(pm25=None, pm10=20.0, co2=400.0)

    def test_negative_values_accepted(self):
        """Pydantic float does not enforce positivity."""
        aq = AirQualityData(pm25=-1.0, pm10=-2.0, co2=-3.0)
        assert aq.pm25 == -1.0


# ===================================================================
# AgentData with new nested fields
# ===================================================================

class TestAgentDataWithNewFields:
    def _valid_payload(self):
        return {
            "user_id": 1,
            "accelerometer": {"x": 0.1, "y": 0.2, "z": 0.3},
            "gps": {"latitude": 50.45, "longitude": 30.52},
            "rain": {"intensity": 0.5},
            "traffic_light": {
                "state": "green",
                "duration": 35,
                "gps": {"latitude": 50.45, "longitude": 30.52},
            },
            "air_quality": {"pm25": 12.5, "pm10": 28.3, "co2": 420.0},
            "temperature": 22.5,
            "timestamp": "2024-01-15T10:30:00",
        }

    def test_create_from_dict(self):
        ad = AgentData(**self._valid_payload())
        assert ad.user_id == 1
        assert isinstance(ad.traffic_light, TrafficLightData)
        assert isinstance(ad.air_quality, AirQualityData)

    def test_traffic_light_accessible(self):
        ad = AgentData(**self._valid_payload())
        assert ad.traffic_light.state == "green"
        assert ad.traffic_light.duration == 35
        assert ad.traffic_light.gps.latitude == 50.45

    def test_air_quality_accessible(self):
        ad = AgentData(**self._valid_payload())
        assert ad.air_quality.pm25 == 12.5
        assert ad.air_quality.pm10 == 28.3
        assert ad.air_quality.co2 == 420.0

    def test_missing_traffic_light_raises(self):
        payload = self._valid_payload()
        del payload["traffic_light"]
        with pytest.raises(ValidationError):
            AgentData(**payload)

    def test_missing_air_quality_raises(self):
        payload = self._valid_payload()
        del payload["air_quality"]
        with pytest.raises(ValidationError):
            AgentData(**payload)

    def test_invalid_timestamp_raises(self):
        payload = self._valid_payload()
        payload["timestamp"] = "not-a-date"
        with pytest.raises((ValidationError, ValueError)):
            AgentData(**payload)

    def test_model_dump_includes_new_fields(self):
        ad = AgentData(**self._valid_payload())
        d = ad.model_dump()
        assert "traffic_light" in d
        assert "air_quality" in d
        assert d["traffic_light"]["state"] == "green"
        assert d["air_quality"]["pm25"] == 12.5

    def test_existing_fields_still_work(self):
        ad = AgentData(**self._valid_payload())
        assert ad.accelerometer.x == 0.1
        assert ad.gps.latitude == 50.45
        assert ad.rain.intensity == 0.5
        assert ad.temperature == 22.5

    def test_empty_dict_for_traffic_light_raises(self):
        """An empty dict is missing required fields for TrafficLightData."""
        payload = self._valid_payload()
        payload["traffic_light"] = {}
        with pytest.raises(ValidationError):
            AgentData(**payload)

    def test_empty_dict_for_air_quality_raises(self):
        """An empty dict is missing required fields for AirQualityData."""
        payload = self._valid_payload()
        payload["air_quality"] = {}
        with pytest.raises(ValidationError):
            AgentData(**payload)

    def test_none_for_traffic_light_raises(self):
        payload = self._valid_payload()
        payload["traffic_light"] = None
        with pytest.raises(ValidationError):
            AgentData(**payload)


# ===================================================================
# ProcessedAgentData with new state fields
# ===================================================================

class TestProcessedAgentDataWithNewStates:
    def _valid_processed(self):
        agent = {
            "user_id": 1,
            "accelerometer": {"x": 0.1, "y": 0.2, "z": 0.3},
            "gps": {"latitude": 50.45, "longitude": 30.52},
            "rain": {"intensity": 0.5},
            "traffic_light": {
                "state": "green",
                "duration": 35,
                "gps": {"latitude": 50.45, "longitude": 30.52},
            },
            "air_quality": {"pm25": 12.5, "pm10": 28.3, "co2": 420.0},
            "temperature": 22.5,
            "timestamp": "2024-01-15T10:30:00",
        }
        return {
            "road_state": "Even",
            "rain_state": "Shower",
            "traffic_light_state": "Safe to go",
            "air_quality_state": "Moderate",
            "agent_data": agent,
        }

    def test_create_valid(self):
        pad = ProcessedAgentData(**self._valid_processed())
        assert pad.road_state == "Even"
        assert pad.rain_state == "Shower"
        assert pad.traffic_light_state == "Safe to go"
        assert pad.air_quality_state == "Moderate"

    def test_missing_traffic_light_state_raises(self):
        payload = self._valid_processed()
        del payload["traffic_light_state"]
        with pytest.raises(ValidationError):
            ProcessedAgentData(**payload)

    def test_missing_air_quality_state_raises(self):
        payload = self._valid_processed()
        del payload["air_quality_state"]
        with pytest.raises(ValidationError):
            ProcessedAgentData(**payload)

    def test_all_traffic_light_states(self):
        for state in ("Safe to go", "Caution", "Stop"):
            payload = self._valid_processed()
            payload["traffic_light_state"] = state
            pad = ProcessedAgentData(**payload)
            assert pad.traffic_light_state == state

    def test_all_air_quality_states(self):
        for state in (
            "Good", "Moderate", "Unhealthy for Sensitive",
            "Unhealthy", "Very Unhealthy", "Hazardous",
        ):
            payload = self._valid_processed()
            payload["air_quality_state"] = state
            pad = ProcessedAgentData(**payload)
            assert pad.air_quality_state == state

    def test_model_dump_includes_new_states(self):
        pad = ProcessedAgentData(**self._valid_processed())
        d = pad.model_dump()
        assert d["traffic_light_state"] == "Safe to go"
        assert d["air_quality_state"] == "Moderate"
        assert "agent_data" in d

    def test_nested_agent_data_traffic_light(self):
        pad = ProcessedAgentData(**self._valid_processed())
        assert pad.agent_data.traffic_light.state == "green"

    def test_nested_agent_data_air_quality(self):
        pad = ProcessedAgentData(**self._valid_processed())
        assert pad.agent_data.air_quality.pm25 == 12.5
