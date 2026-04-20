"""
Tests for Lab 2 data-processing logic in the Edge service:
  - process_traffic_light_state()
  - process_air_quality_state()
  - process_agent_data() returning all 4 states

The processing functions and Pydantic models are replicated inline
so the tests run without Docker or imports from the Edge service.
"""

import pytest
from datetime import datetime
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Self-contained Pydantic models (minimal replicas)
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
    state: str
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
            raise ValueError("Invalid timestamp format.")


class ProcessedAgentData(BaseModel):
    road_state: str
    rain_state: str
    traffic_light_state: str
    air_quality_state: str
    agent_data: AgentData


# ---------------------------------------------------------------------------
# Self-contained processing functions (replica of planned Edge logic)
# ---------------------------------------------------------------------------

def process_traffic_light_state(agent_data: AgentData) -> str:
    """Classify safety based on traffic light state and time remaining."""
    state = agent_data.traffic_light.state
    duration = agent_data.traffic_light.duration
    if state == "green" and duration > 10:
        return "Safe to go"
    elif state == "green" and duration <= 10:
        return "Caution"
    elif state == "yellow":
        return "Caution"
    else:  # red
        return "Stop"


def process_air_quality_state(agent_data: AgentData) -> str:
    """Classify air quality based on PM2.5 (AQI standard)."""
    pm25 = agent_data.air_quality.pm25
    if pm25 <= 12:
        return "Good"
    elif pm25 <= 35.4:
        return "Moderate"
    elif pm25 <= 55.4:
        return "Unhealthy for Sensitive"
    elif pm25 <= 150.4:
        return "Unhealthy"
    elif pm25 <= 250.4:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def process_rain_state(agent_data: AgentData) -> str:
    """Existing rain classification (from Lab 1)."""
    intensity = agent_data.rain.intensity
    if intensity == 0:
        return "Clear"
    elif 0 < intensity <= 0.2:
        return "Drizzle"
    elif 0.2 < intensity <= 0.4:
        return "Sprinkle"
    elif 0.4 < intensity <= 0.6:
        return "Shower"
    elif 0.6 < intensity <= 0.8:
        return "Rain"
    elif 0.8 < intensity <= 1:
        return "Downpour"
    else:
        return "Invalid intensity"


def process_agent_data(agent_data: AgentData) -> ProcessedAgentData:
    """Full processing returning all 4 states."""
    road_state = "Even"  # simplified for testing
    rain_state = process_rain_state(agent_data)
    traffic_light_state = process_traffic_light_state(agent_data)
    air_quality_state = process_air_quality_state(agent_data)
    return ProcessedAgentData(
        road_state=road_state,
        rain_state=rain_state,
        traffic_light_state=traffic_light_state,
        air_quality_state=air_quality_state,
        agent_data=agent_data,
    )


# ---------------------------------------------------------------------------
# Helper to build an AgentData instance quickly
# ---------------------------------------------------------------------------

def _make_agent(
    traffic_state="green",
    traffic_duration=35,
    pm25=10.0,
    pm10=20.0,
    co2=400.0,
    rain_intensity=0.0,
):
    return AgentData(
        user_id=1,
        accelerometer=AccelerometerData(x=0.0, y=0.0, z=0.0),
        gps=GpsData(latitude=50.45, longitude=30.52),
        rain=RainData(intensity=rain_intensity),
        traffic_light=TrafficLightData(
            state=traffic_state,
            duration=traffic_duration,
            gps=GpsData(latitude=50.45, longitude=30.52),
        ),
        air_quality=AirQualityData(pm25=pm25, pm10=pm10, co2=co2),
        temperature=22.5,
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
    )


# ===================================================================
# process_traffic_light_state()
# ===================================================================

class TestProcessTrafficLightState:
    # ---- green + duration > 10 => "Safe to go" ----
    def test_green_long_duration(self):
        ad = _make_agent(traffic_state="green", traffic_duration=30)
        assert process_traffic_light_state(ad) == "Safe to go"

    def test_green_duration_11(self):
        ad = _make_agent(traffic_state="green", traffic_duration=11)
        assert process_traffic_light_state(ad) == "Safe to go"

    # ---- green + duration <= 10 => "Caution" ----
    def test_green_duration_10_boundary(self):
        ad = _make_agent(traffic_state="green", traffic_duration=10)
        assert process_traffic_light_state(ad) == "Caution"

    def test_green_duration_5(self):
        ad = _make_agent(traffic_state="green", traffic_duration=5)
        assert process_traffic_light_state(ad) == "Caution"

    def test_green_duration_1(self):
        ad = _make_agent(traffic_state="green", traffic_duration=1)
        assert process_traffic_light_state(ad) == "Caution"

    def test_green_duration_0(self):
        ad = _make_agent(traffic_state="green", traffic_duration=0)
        assert process_traffic_light_state(ad) == "Caution"

    # ---- yellow => "Caution" ----
    def test_yellow(self):
        ad = _make_agent(traffic_state="yellow", traffic_duration=4)
        assert process_traffic_light_state(ad) == "Caution"

    def test_yellow_long_duration(self):
        ad = _make_agent(traffic_state="yellow", traffic_duration=20)
        assert process_traffic_light_state(ad) == "Caution"

    def test_yellow_zero_duration(self):
        ad = _make_agent(traffic_state="yellow", traffic_duration=0)
        assert process_traffic_light_state(ad) == "Caution"

    # ---- red => "Stop" ----
    def test_red(self):
        ad = _make_agent(traffic_state="red", traffic_duration=45)
        assert process_traffic_light_state(ad) == "Stop"

    def test_red_short_duration(self):
        ad = _make_agent(traffic_state="red", traffic_duration=1)
        assert process_traffic_light_state(ad) == "Stop"

    def test_red_zero_duration(self):
        ad = _make_agent(traffic_state="red", traffic_duration=0)
        assert process_traffic_light_state(ad) == "Stop"

    # ---- unknown state falls into else => "Stop" ----
    def test_unknown_state_falls_to_stop(self):
        ad = _make_agent(traffic_state="broken", traffic_duration=10)
        assert process_traffic_light_state(ad) == "Stop"


# ===================================================================
# process_rain_state()
# ===================================================================

class TestProcessRainState:
    """Tests for rain intensity classification boundaries."""

    @pytest.mark.parametrize(
        "intensity, expected",
        [
            (0.0, "Clear"),
            (0.1, "Drizzle"),
            (0.2, "Drizzle"),
            (0.21, "Sprinkle"),
            (0.3, "Sprinkle"),
            (0.4, "Sprinkle"),
            (0.41, "Shower"),
            (0.5, "Shower"),
            (0.6, "Shower"),
            (0.61, "Rain"),
            (0.7, "Rain"),
            (0.8, "Rain"),
            (0.81, "Downpour"),
            (0.9, "Downpour"),
            (1.0, "Downpour"),
            (1.01, "Invalid intensity"),
            (-0.1, "Invalid intensity"),
        ],
    )
    def test_rain_boundary_parametrized(self, intensity, expected):
        ad = _make_agent(rain_intensity=intensity)
        assert process_rain_state(ad) == expected

    def test_zero_intensity_is_clear(self):
        ad = _make_agent(rain_intensity=0)
        assert process_rain_state(ad) == "Clear"

    def test_negative_intensity_is_invalid(self):
        ad = _make_agent(rain_intensity=-0.5)
        assert process_rain_state(ad) == "Invalid intensity"


# ===================================================================
# process_air_quality_state()
# ===================================================================

class TestProcessAirQualityState:
    # ---- Good: pm25 <= 12 ----
    def test_good_zero(self):
        ad = _make_agent(pm25=0.0)
        assert process_air_quality_state(ad) == "Good"

    def test_good_low(self):
        ad = _make_agent(pm25=5.0)
        assert process_air_quality_state(ad) == "Good"

    def test_good_boundary_12(self):
        ad = _make_agent(pm25=12.0)
        assert process_air_quality_state(ad) == "Good"

    # ---- Moderate: 12 < pm25 <= 35.4 ----
    def test_moderate_just_above_12(self):
        ad = _make_agent(pm25=12.1)
        assert process_air_quality_state(ad) == "Moderate"

    def test_moderate_mid(self):
        ad = _make_agent(pm25=25.0)
        assert process_air_quality_state(ad) == "Moderate"

    def test_moderate_boundary_35_4(self):
        ad = _make_agent(pm25=35.4)
        assert process_air_quality_state(ad) == "Moderate"

    # ---- Unhealthy for Sensitive: 35.4 < pm25 <= 55.4 ----
    def test_sensitive_just_above_35_4(self):
        ad = _make_agent(pm25=35.5)
        assert process_air_quality_state(ad) == "Unhealthy for Sensitive"

    def test_sensitive_mid(self):
        ad = _make_agent(pm25=45.0)
        assert process_air_quality_state(ad) == "Unhealthy for Sensitive"

    def test_sensitive_boundary_55_4(self):
        ad = _make_agent(pm25=55.4)
        assert process_air_quality_state(ad) == "Unhealthy for Sensitive"

    # ---- Unhealthy: 55.4 < pm25 <= 150.4 ----
    def test_unhealthy_just_above_55_4(self):
        ad = _make_agent(pm25=55.5)
        assert process_air_quality_state(ad) == "Unhealthy"

    def test_unhealthy_mid(self):
        ad = _make_agent(pm25=100.0)
        assert process_air_quality_state(ad) == "Unhealthy"

    def test_unhealthy_boundary_150_4(self):
        ad = _make_agent(pm25=150.4)
        assert process_air_quality_state(ad) == "Unhealthy"

    # ---- Very Unhealthy: 150.4 < pm25 <= 250.4 ----
    def test_very_unhealthy_just_above_150_4(self):
        ad = _make_agent(pm25=150.5)
        assert process_air_quality_state(ad) == "Very Unhealthy"

    def test_very_unhealthy_mid(self):
        ad = _make_agent(pm25=200.0)
        assert process_air_quality_state(ad) == "Very Unhealthy"

    def test_very_unhealthy_boundary_250_4(self):
        ad = _make_agent(pm25=250.4)
        assert process_air_quality_state(ad) == "Very Unhealthy"

    # ---- Hazardous: pm25 > 250.4 ----
    def test_hazardous_just_above_250_4(self):
        ad = _make_agent(pm25=250.5)
        assert process_air_quality_state(ad) == "Hazardous"

    def test_hazardous_high(self):
        ad = _make_agent(pm25=500.0)
        assert process_air_quality_state(ad) == "Hazardous"

    def test_hazardous_extreme(self):
        ad = _make_agent(pm25=999.0)
        assert process_air_quality_state(ad) == "Hazardous"

    # ---- Edge: exactly at each AQI breakpoint ----
    @pytest.mark.parametrize(
        "pm25, expected",
        [
            (12.0, "Good"),
            (12.01, "Moderate"),
            (35.4, "Moderate"),
            (35.41, "Unhealthy for Sensitive"),
            (55.4, "Unhealthy for Sensitive"),
            (55.41, "Unhealthy"),
            (150.4, "Unhealthy"),
            (150.41, "Very Unhealthy"),
            (250.4, "Very Unhealthy"),
            (250.41, "Hazardous"),
        ],
    )
    def test_boundary_parametrized(self, pm25, expected):
        ad = _make_agent(pm25=pm25)
        assert process_air_quality_state(ad) == expected


# ===================================================================
# process_agent_data() — full pipeline returning all 4 states
# ===================================================================

class TestProcessAgentData:
    def test_returns_processed_agent_data(self):
        ad = _make_agent()
        result = process_agent_data(ad)
        assert isinstance(result, ProcessedAgentData)

    def test_all_four_states_present(self):
        ad = _make_agent(
            traffic_state="green",
            traffic_duration=30,
            pm25=10.0,
            rain_intensity=0.5,
        )
        result = process_agent_data(ad)
        assert result.road_state is not None
        assert result.rain_state == "Shower"
        assert result.traffic_light_state == "Safe to go"
        assert result.air_quality_state == "Good"

    def test_agent_data_preserved(self):
        ad = _make_agent()
        result = process_agent_data(ad)
        assert result.agent_data.user_id == ad.user_id
        assert result.agent_data.temperature == ad.temperature

    def test_red_light_and_hazardous_air(self):
        ad = _make_agent(traffic_state="red", traffic_duration=40, pm25=300.0)
        result = process_agent_data(ad)
        assert result.traffic_light_state == "Stop"
        assert result.air_quality_state == "Hazardous"

    def test_yellow_light_and_moderate_air(self):
        ad = _make_agent(traffic_state="yellow", traffic_duration=3, pm25=25.0)
        result = process_agent_data(ad)
        assert result.traffic_light_state == "Caution"
        assert result.air_quality_state == "Moderate"

    def test_green_short_duration_and_good_air(self):
        ad = _make_agent(traffic_state="green", traffic_duration=5, pm25=8.0)
        result = process_agent_data(ad)
        assert result.traffic_light_state == "Caution"
        assert result.air_quality_state == "Good"

    def test_rain_state_clear(self):
        ad = _make_agent(rain_intensity=0.0)
        result = process_agent_data(ad)
        assert result.rain_state == "Clear"

    def test_rain_state_downpour(self):
        ad = _make_agent(rain_intensity=0.9)
        result = process_agent_data(ad)
        assert result.rain_state == "Downpour"

    def test_rain_state_drizzle(self):
        ad = _make_agent(rain_intensity=0.1)
        result = process_agent_data(ad)
        assert result.rain_state == "Drizzle"

    def test_rain_state_rain(self):
        ad = _make_agent(rain_intensity=0.7)
        result = process_agent_data(ad)
        assert result.rain_state == "Rain"

    def test_rain_state_invalid_intensity(self):
        ad = _make_agent(rain_intensity=1.5)
        result = process_agent_data(ad)
        assert result.rain_state == "Invalid intensity"

    def test_model_dump_has_all_keys(self):
        ad = _make_agent()
        result = process_agent_data(ad)
        d = result.model_dump()
        assert "road_state" in d
        assert "rain_state" in d
        assert "traffic_light_state" in d
        assert "air_quality_state" in d
        assert "agent_data" in d
