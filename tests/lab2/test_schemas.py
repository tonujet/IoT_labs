"""
Tests for Lab 2 Marshmallow schemas: TrafficLightSchema, AirQualitySchema,
and the updated AggregatedDataSchema.

The schemas live in the Agent codebase and are used to serialize/deserialize
data between the Agent and the Edge.
"""

import pytest
from datetime import datetime
from marshmallow import Schema, fields, ValidationError


# ---------------------------------------------------------------------------
# Self-contained schema replicas matching the Lab 2 plan specification.
# ---------------------------------------------------------------------------

class GpsSchema(Schema):
    longitude = fields.Float()
    latitude = fields.Float()


class AccelerometerSchema(Schema):
    x = fields.Int()
    y = fields.Int()
    z = fields.Int()


class ParkingSchema(Schema):
    empty_count = fields.Float()
    gps = fields.Nested(GpsSchema)


class RainSchema(Schema):
    intensity = fields.Float()


class TrafficLightSchema(Schema):
    state = fields.Str()
    duration = fields.Int()
    gps = fields.Nested(GpsSchema)


class AirQualitySchema(Schema):
    pm25 = fields.Float()
    pm10 = fields.Float()
    co2 = fields.Float()


class AggregatedDataSchema(Schema):
    accelerometer = fields.Nested(AccelerometerSchema)
    gps = fields.Nested(GpsSchema)
    parking = fields.Nested(ParkingSchema)
    rain = fields.Nested(RainSchema)
    traffic_light = fields.Nested(TrafficLightSchema)
    air_quality = fields.Nested(AirQualitySchema)
    temperature = fields.Float()
    timestamp = fields.DateTime("iso")
    user_id = fields.Int()


# ===================================================================
# TrafficLightSchema
# ===================================================================

class TestTrafficLightSchema:
    schema = TrafficLightSchema()

    def test_serialize(self):
        data = {
            "state": "green",
            "duration": 35,
            "gps": {"longitude": 30.52, "latitude": 50.45},
        }
        result = self.schema.dump(data)
        assert result["state"] == "green"
        assert result["duration"] == 35
        assert result["gps"]["longitude"] == 30.52

    def test_deserialize(self):
        raw = {
            "state": "red",
            "duration": 45,
            "gps": {"longitude": 30.0, "latitude": 50.0},
        }
        result = self.schema.load(raw)
        assert result["state"] == "red"
        assert result["duration"] == 45
        assert result["gps"]["longitude"] == 30.0
        assert result["gps"]["latitude"] == 50.0

    def test_deserialize_yellow(self):
        raw = {
            "state": "yellow",
            "duration": 4,
            "gps": {"longitude": 0.0, "latitude": 0.0},
        }
        result = self.schema.load(raw)
        assert result["state"] == "yellow"
        assert result["duration"] == 4

    def test_missing_state_field(self):
        """Missing fields should still load (fields are not required by default)."""
        raw = {"duration": 10, "gps": {"longitude": 0, "latitude": 0}}
        result = self.schema.load(raw)
        assert "state" not in result

    def test_missing_gps_field(self):
        raw = {"state": "green", "duration": 10}
        result = self.schema.load(raw)
        assert "gps" not in result

    def test_invalid_duration_type(self):
        """String for an Int field should raise a validation error."""
        raw = {
            "state": "green",
            "duration": "not_a_number",
            "gps": {"longitude": 0, "latitude": 0},
        }
        with pytest.raises(ValidationError):
            self.schema.load(raw)

    def test_round_trip(self):
        data = {
            "state": "green",
            "duration": 25,
            "gps": {"longitude": 30.52, "latitude": 50.45},
        }
        dumped = self.schema.dump(data)
        loaded = self.schema.load(dumped)
        assert loaded["state"] == data["state"]
        assert loaded["duration"] == data["duration"]

    def test_extra_fields_rejected(self):
        """Marshmallow 4 raises ValidationError on unknown fields by default."""
        raw = {
            "state": "green",
            "duration": 10,
            "gps": {"longitude": 0, "latitude": 0},
            "extra_field": "should cause error",
        }
        with pytest.raises(ValidationError):
            self.schema.load(raw)

    def test_empty_payload(self):
        """Empty dict should load without error (no required fields)."""
        result = self.schema.load({})
        assert result == {}

    def test_zero_duration(self):
        raw = {
            "state": "green",
            "duration": 0,
            "gps": {"longitude": 0, "latitude": 0},
        }
        result = self.schema.load(raw)
        assert result["duration"] == 0


# ===================================================================
# AirQualitySchema
# ===================================================================

class TestAirQualitySchema:
    schema = AirQualitySchema()

    def test_serialize(self):
        data = {"pm25": 12.5, "pm10": 28.3, "co2": 420.0}
        result = self.schema.dump(data)
        assert result["pm25"] == 12.5
        assert result["pm10"] == 28.3
        assert result["co2"] == 420.0

    def test_deserialize(self):
        raw = {"pm25": 55.0, "pm10": 80.0, "co2": 500.0}
        result = self.schema.load(raw)
        assert result["pm25"] == 55.0

    def test_zero_values(self):
        raw = {"pm25": 0.0, "pm10": 0.0, "co2": 0.0}
        result = self.schema.load(raw)
        assert result["pm25"] == 0.0
        assert result["pm10"] == 0.0
        assert result["co2"] == 0.0

    def test_missing_field(self):
        raw = {"pm25": 10.0, "pm10": 20.0}
        result = self.schema.load(raw)
        assert "co2" not in result

    def test_invalid_type_string(self):
        raw = {"pm25": "bad", "pm10": 20.0, "co2": 400.0}
        with pytest.raises(ValidationError):
            self.schema.load(raw)

    def test_round_trip(self):
        data = {"pm25": 35.4, "pm10": 60.0, "co2": 450.0}
        dumped = self.schema.dump(data)
        loaded = self.schema.load(dumped)
        assert loaded["pm25"] == pytest.approx(data["pm25"])
        assert loaded["co2"] == pytest.approx(data["co2"])

    def test_negative_values_accepted(self):
        """Marshmallow Float field does not enforce positivity by default."""
        raw = {"pm25": -1.0, "pm10": -2.0, "co2": -3.0}
        result = self.schema.load(raw)
        assert result["pm25"] == -1.0

    def test_high_values(self):
        raw = {"pm25": 999.9, "pm10": 999.9, "co2": 9999.9}
        result = self.schema.load(raw)
        assert result["pm25"] == 999.9

    def test_empty_payload(self):
        """Empty dict should load without error (no required fields)."""
        result = self.schema.load({})
        assert result == {}

    def test_extra_fields_rejected(self):
        """Marshmallow 4 rejects unknown fields by default."""
        raw = {"pm25": 10.0, "pm10": 20.0, "co2": 400.0, "unknown": 1}
        with pytest.raises(ValidationError):
            self.schema.load(raw)


# ===================================================================
# AggregatedDataSchema with new fields
# ===================================================================

class TestAggregatedDataSchema:
    schema = AggregatedDataSchema()

    def _full_payload(self, use_datetime=False):
        ts = datetime(2024, 1, 15, 10, 30, 0) if use_datetime else "2024-01-15T10:30:00"
        return {
            "accelerometer": {"x": 1, "y": 2, "z": 3},
            "gps": {"longitude": 30.52, "latitude": 50.45},
            "parking": {
                "empty_count": 5,
                "gps": {"longitude": 30.0, "latitude": 50.0},
            },
            "rain": {"intensity": 0.3},
            "traffic_light": {
                "state": "green",
                "duration": 25,
                "gps": {"longitude": 30.52, "latitude": 50.45},
            },
            "air_quality": {"pm25": 15.0, "pm10": 28.0, "co2": 420.0},
            "temperature": 22.5,
            "timestamp": ts,
            "user_id": 1,
        }

    def test_load_full_payload(self):
        result = self.schema.load(self._full_payload())
        assert result["traffic_light"]["state"] == "green"
        assert result["air_quality"]["pm25"] == 15.0

    def test_dump_full_payload(self):
        result = self.schema.dump(self._full_payload(use_datetime=True))
        assert "traffic_light" in result
        assert "air_quality" in result
        assert result["traffic_light"]["duration"] == 25

    def test_round_trip(self):
        payload = self._full_payload(use_datetime=True)
        dumped = self.schema.dump(payload)
        loaded = self.schema.load(dumped)
        assert loaded["traffic_light"]["state"] == "green"
        assert loaded["air_quality"]["co2"] == pytest.approx(420.0)

    def test_missing_traffic_light_still_loads(self):
        payload = self._full_payload()
        del payload["traffic_light"]
        result = self.schema.load(payload)
        assert "traffic_light" not in result

    def test_missing_air_quality_still_loads(self):
        payload = self._full_payload()
        del payload["air_quality"]
        result = self.schema.load(payload)
        assert "air_quality" not in result

    def test_existing_fields_preserved(self):
        result = self.schema.load(self._full_payload())
        assert result["accelerometer"]["x"] == 1
        assert result["parking"]["empty_count"] == 5
        assert result["rain"]["intensity"] == 0.3

    def test_invalid_timestamp(self):
        payload = self._full_payload()
        payload["timestamp"] = "not-a-date"
        with pytest.raises(ValidationError):
            self.schema.load(payload)

    def test_nested_traffic_light_gps(self):
        result = self.schema.load(self._full_payload())
        tl_gps = result["traffic_light"]["gps"]
        assert tl_gps["longitude"] == 30.52
        assert tl_gps["latitude"] == 50.45

    def test_empty_payload_loads(self):
        """An empty dict should load without error (no required fields)."""
        result = self.schema.load({})
        assert result == {}

    def test_only_new_fields(self):
        """Loading only the new sensor fields should work."""
        payload = {
            "traffic_light": {
                "state": "red",
                "duration": 30,
                "gps": {"longitude": 0.0, "latitude": 0.0},
            },
            "air_quality": {"pm25": 10.0, "pm10": 20.0, "co2": 400.0},
        }
        result = self.schema.load(payload)
        assert result["traffic_light"]["state"] == "red"
        assert result["air_quality"]["pm25"] == 10.0
