"""
Tests for the Lab 2 Store layer: Pydantic models used by the Store API and
the flattening logic that maps nested ProcessedAgentData to DB columns.

The Store receives nested JSON from the Hub, then flattens it into individual
columns for PostgreSQL.  These tests verify:
  - New Pydantic models accept valid data and reject invalid data.
  - The flattening to a DB-ready dict produces all expected columns.
  - New columns (traffic_light_*, pm25, pm10, co2, etc.) are present.

No actual database connection is needed.
"""

import pytest
from datetime import datetime
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Float, DateTime, inspect,
    create_engine,
)


# ---------------------------------------------------------------------------
# Self-contained Pydantic replicas matching the planned Store models.
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
    def check_timestamp(cls, value):
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
# SQLAlchemy table definition (replica of planned Lab 2 schema)
# ---------------------------------------------------------------------------

metadata = MetaData()

processed_agent_data_table = Table(
    "processed_agent_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("road_state", String),
    Column("rain_state", String),
    Column("traffic_light_state", String),
    Column("air_quality_state", String),
    Column("user_id", Integer),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("rain_intensity", Float),
    Column("temperature", Float),
    Column("traffic_light_color", String),
    Column("traffic_light_duration", Integer),
    Column("traffic_light_latitude", Float),
    Column("traffic_light_longitude", Float),
    Column("pm25", Float),
    Column("pm10", Float),
    Column("co2", Float),
    Column("timestamp", DateTime),
)


# ---------------------------------------------------------------------------
# Flattening function (replica of planned INSERT logic)
# ---------------------------------------------------------------------------

def flatten_for_db(record: ProcessedAgentData) -> dict:
    """Flatten nested ProcessedAgentData into a flat dict for DB insert."""
    ad = record.agent_data
    return {
        "road_state": record.road_state,
        "rain_state": record.rain_state,
        "traffic_light_state": record.traffic_light_state,
        "air_quality_state": record.air_quality_state,
        "user_id": ad.user_id,
        "x": ad.accelerometer.x,
        "y": ad.accelerometer.y,
        "z": ad.accelerometer.z,
        "latitude": ad.gps.latitude,
        "longitude": ad.gps.longitude,
        "rain_intensity": ad.rain.intensity,
        "temperature": ad.temperature,
        "traffic_light_color": ad.traffic_light.state,
        "traffic_light_duration": ad.traffic_light.duration,
        "traffic_light_latitude": ad.traffic_light.gps.latitude,
        "traffic_light_longitude": ad.traffic_light.gps.longitude,
        "pm25": ad.air_quality.pm25,
        "pm10": ad.air_quality.pm10,
        "co2": ad.air_quality.co2,
        "timestamp": ad.timestamp,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_processed() -> ProcessedAgentData:
    return ProcessedAgentData(
        road_state="Even",
        rain_state="Shower",
        traffic_light_state="Safe to go",
        air_quality_state="Moderate",
        agent_data=AgentData(
            user_id=1,
            accelerometer=AccelerometerData(x=0.1, y=0.2, z=0.3),
            gps=GpsData(latitude=50.45, longitude=30.52),
            rain=RainData(intensity=0.5),
            traffic_light=TrafficLightData(
                state="green",
                duration=35,
                gps=GpsData(latitude=50.46, longitude=30.53),
            ),
            air_quality=AirQualityData(pm25=12.5, pm10=28.3, co2=420.0),
            temperature=22.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
        ),
    )


# ===================================================================
# Table definition tests
# ===================================================================

class TestTableDefinition:
    def test_table_has_traffic_light_state_column(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "traffic_light_state" in col_names

    def test_table_has_air_quality_state_column(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "air_quality_state" in col_names

    def test_table_has_traffic_light_color(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "traffic_light_color" in col_names

    def test_table_has_traffic_light_duration(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "traffic_light_duration" in col_names

    def test_table_has_traffic_light_latitude(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "traffic_light_latitude" in col_names

    def test_table_has_traffic_light_longitude(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "traffic_light_longitude" in col_names

    def test_table_has_pm25(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "pm25" in col_names

    def test_table_has_pm10(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "pm10" in col_names

    def test_table_has_co2(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        assert "co2" in col_names

    def test_existing_columns_preserved(self):
        col_names = {c.name for c in processed_agent_data_table.columns}
        for expected in (
            "id", "road_state", "rain_state", "user_id",
            "x", "y", "z", "latitude", "longitude",
            "rain_intensity", "temperature", "timestamp",
        ):
            assert expected in col_names, f"Missing column: {expected}"

    def test_total_column_count(self):
        """Lab 2 table should have 21 columns (12 original + 9 new)."""
        assert len(processed_agent_data_table.columns) == 21

    def test_new_column_types(self):
        col_type_map = {
            c.name: type(c.type) for c in processed_agent_data_table.columns
        }
        assert col_type_map["traffic_light_state"] is String
        assert col_type_map["air_quality_state"] is String
        assert col_type_map["traffic_light_color"] is String
        assert col_type_map["traffic_light_duration"] is Integer
        assert col_type_map["traffic_light_latitude"] is Float
        assert col_type_map["traffic_light_longitude"] is Float
        assert col_type_map["pm25"] is Float
        assert col_type_map["pm10"] is Float
        assert col_type_map["co2"] is Float


# ===================================================================
# Flattening tests
# ===================================================================

class TestFlattenForDb:
    def test_flatten_returns_dict(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert isinstance(flat, dict)

    def test_flatten_has_all_expected_keys(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        expected_keys = {
            "road_state", "rain_state", "traffic_light_state",
            "air_quality_state", "user_id", "x", "y", "z",
            "latitude", "longitude", "rain_intensity", "temperature",
            "traffic_light_color", "traffic_light_duration",
            "traffic_light_latitude", "traffic_light_longitude",
            "pm25", "pm10", "co2", "timestamp",
        }
        assert set(flat.keys()) == expected_keys

    def test_flatten_traffic_light_color(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["traffic_light_color"] == "green"

    def test_flatten_traffic_light_duration(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["traffic_light_duration"] == 35

    def test_flatten_traffic_light_gps(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["traffic_light_latitude"] == 50.46
        assert flat["traffic_light_longitude"] == 30.53

    def test_flatten_pm25(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["pm25"] == 12.5

    def test_flatten_pm10(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["pm10"] == 28.3

    def test_flatten_co2(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["co2"] == 420.0

    def test_flatten_preserves_existing_fields(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["road_state"] == "Even"
        assert flat["rain_state"] == "Shower"
        assert flat["user_id"] == 1
        assert flat["x"] == 0.1
        assert flat["latitude"] == 50.45
        assert flat["temperature"] == 22.5

    def test_flatten_traffic_light_state(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["traffic_light_state"] == "Safe to go"

    def test_flatten_air_quality_state(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert flat["air_quality_state"] == "Moderate"

    def test_flatten_timestamp_is_datetime(self):
        record = _make_processed()
        flat = flatten_for_db(record)
        assert isinstance(flat["timestamp"], datetime)

    def test_flatten_keys_match_table_columns(self):
        """Every key in the flat dict should correspond to a table column (except 'id')."""
        record = _make_processed()
        flat = flatten_for_db(record)
        table_cols = {c.name for c in processed_agent_data_table.columns} - {"id"}
        assert set(flat.keys()) == table_cols


# ===================================================================
# Store Pydantic model validation tests
# ===================================================================

class TestStorePydanticModels:
    def test_processed_agent_data_valid(self):
        record = _make_processed()
        assert record.traffic_light_state == "Safe to go"
        assert record.air_quality_state == "Moderate"

    def test_processed_agent_data_missing_traffic_state_raises(self):
        with pytest.raises(ValidationError):
            ProcessedAgentData(
                road_state="Even",
                rain_state="Shower",
                air_quality_state="Good",
                agent_data=_make_processed().agent_data,
            )

    def test_processed_agent_data_missing_air_state_raises(self):
        with pytest.raises(ValidationError):
            ProcessedAgentData(
                road_state="Even",
                rain_state="Shower",
                traffic_light_state="Stop",
                agent_data=_make_processed().agent_data,
            )

    def test_agent_data_missing_traffic_light_raises(self):
        with pytest.raises(ValidationError):
            AgentData(
                user_id=1,
                accelerometer=AccelerometerData(x=0, y=0, z=0),
                gps=GpsData(latitude=0, longitude=0),
                rain=RainData(intensity=0),
                air_quality=AirQualityData(pm25=0, pm10=0, co2=0),
                temperature=0,
                timestamp=datetime.now(),
            )

    def test_agent_data_missing_air_quality_raises(self):
        with pytest.raises(ValidationError):
            AgentData(
                user_id=1,
                accelerometer=AccelerometerData(x=0, y=0, z=0),
                gps=GpsData(latitude=0, longitude=0),
                rain=RainData(intensity=0),
                traffic_light=TrafficLightData(
                    state="red", duration=0,
                    gps=GpsData(latitude=0, longitude=0),
                ),
                temperature=0,
                timestamp=datetime.now(),
            )

    def test_model_dump_round_trip(self):
        record = _make_processed()
        d = record.model_dump()
        restored = ProcessedAgentData(**d)
        assert restored.traffic_light_state == record.traffic_light_state
        assert restored.air_quality_state == record.air_quality_state
        assert restored.agent_data.traffic_light.state == "green"
        assert restored.agent_data.air_quality.pm25 == 12.5

    def test_zero_air_quality_values(self):
        """Zero values for air quality should be accepted."""
        record = ProcessedAgentData(
            road_state="Even",
            rain_state="Clear",
            traffic_light_state="Stop",
            air_quality_state="Good",
            agent_data=AgentData(
                user_id=1,
                accelerometer=AccelerometerData(x=0, y=0, z=0),
                gps=GpsData(latitude=0, longitude=0),
                rain=RainData(intensity=0),
                traffic_light=TrafficLightData(
                    state="red", duration=0,
                    gps=GpsData(latitude=0, longitude=0),
                ),
                air_quality=AirQualityData(pm25=0.0, pm10=0.0, co2=0.0),
                temperature=0,
                timestamp=datetime.now(),
            ),
        )
        flat = flatten_for_db(record)
        assert flat["pm25"] == 0.0
        assert flat["pm10"] == 0.0
        assert flat["co2"] == 0.0

    def test_flatten_no_extra_keys(self):
        """Flattened dict should not contain unexpected keys."""
        record = _make_processed()
        flat = flatten_for_db(record)
        table_cols = {c.name for c in processed_agent_data_table.columns} - {"id"}
        assert set(flat.keys()) == table_cols


# ===================================================================
# SQLite integration test (in-memory, no PostgreSQL needed)
# ===================================================================

class TestSqliteIntegration:
    """
    Uses an in-memory SQLite database to verify that the table schema
    is valid and that flattened data can actually be inserted.
    """

    @pytest.fixture
    def engine(self):
        eng = create_engine("sqlite:///:memory:")
        metadata.create_all(eng)
        return eng

    def test_table_creates_without_error(self, engine):
        """Table creation should succeed with the Lab 2 schema."""
        insp = inspect(engine)
        assert "processed_agent_data" in insp.get_table_names()

    def test_insert_flattened_record(self, engine):
        record = _make_processed()
        flat = flatten_for_db(record)
        with engine.connect() as conn:
            conn.execute(processed_agent_data_table.insert().values(**flat))
            conn.commit()
            rows = conn.execute(processed_agent_data_table.select()).fetchall()
            assert len(rows) == 1

    def test_inserted_values_correct(self, engine):
        record = _make_processed()
        flat = flatten_for_db(record)
        with engine.connect() as conn:
            conn.execute(processed_agent_data_table.insert().values(**flat))
            conn.commit()
            row = conn.execute(processed_agent_data_table.select()).fetchone()
            mapping = row._mapping
            assert mapping["traffic_light_state"] == "Safe to go"
            assert mapping["air_quality_state"] == "Moderate"
            assert mapping["traffic_light_color"] == "green"
            assert mapping["pm25"] == 12.5
            assert mapping["pm10"] == 28.3
            assert mapping["co2"] == 420.0

    def test_insert_multiple_records(self, engine):
        states = [
            ("Stop", "Hazardous", "red"),
            ("Caution", "Good", "yellow"),
            ("Safe to go", "Moderate", "green"),
        ]
        with engine.connect() as conn:
            for tl_state, aq_state, color in states:
                record = ProcessedAgentData(
                    road_state="Even",
                    rain_state="Clear",
                    traffic_light_state=tl_state,
                    air_quality_state=aq_state,
                    agent_data=AgentData(
                        user_id=1,
                        accelerometer=AccelerometerData(x=0, y=0, z=0),
                        gps=GpsData(latitude=0, longitude=0),
                        rain=RainData(intensity=0),
                        traffic_light=TrafficLightData(
                            state=color, duration=10,
                            gps=GpsData(latitude=0, longitude=0),
                        ),
                        air_quality=AirQualityData(pm25=5, pm10=10, co2=400),
                        temperature=20,
                        timestamp=datetime.now(),
                    ),
                )
                flat = flatten_for_db(record)
                conn.execute(processed_agent_data_table.insert().values(**flat))
            conn.commit()
            rows = conn.execute(processed_agent_data_table.select()).fetchall()
            assert len(rows) == 3
