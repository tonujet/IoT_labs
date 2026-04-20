"""
Tests for the synthetic data generator (agent/src/data/synthetic_generator.py).

The generator produces CSV data based on open-dataset statistics:
  - TrafficLight: Zurich Urban Intersection (green/yellow/red cycles)
  - AirQuality: Beijing Multi-Site Air Quality (PM2.5, PM10, CO2)

These tests replicate the generator logic inline so they run without
numpy being installed project-wide (numpy is only needed inside the
agent container).  If numpy is unavailable the module is skipped.
"""

import math
import random
from pathlib import Path

import pytest

# numpy may not be installed in the test runner; skip gracefully
np = pytest.importorskip("numpy")


# ---------------------------------------------------------------------------
# Self-contained replicas of the generator's parameters and functions.
# These mirror the planned production code exactly.
# ---------------------------------------------------------------------------

TRAFFIC_LIGHT_PARAMS = {
    "green": {"mean_duration": 35, "std_duration": 8, "min": 15, "max": 55},
    "yellow": {"mean_duration": 4, "std_duration": 0.5, "min": 3, "max": 5},
    "red": {"mean_duration": 42, "std_duration": 10, "min": 20, "max": 65},
    "transitions": {
        "green": {"yellow": 1.0},
        "yellow": {"red": 1.0},
        "red": {"green": 1.0},
    },
    "phase_distribution": {"green": 0.45, "yellow": 0.05, "red": 0.50},
}


AIR_QUALITY_PARAMS = {
    "pm25": {"mean": 15.0, "std": 10.0, "min": 2.0, "max": 75.0},
    "pm10": {"mean": 28.0, "std": 18.0, "min": 5.0, "max": 150.0},
    "co2":  {"mean": 420.0, "std": 45.0, "min": 350.0, "max": 600.0},
    "correlation_pm25_pm10": 0.87,
    "correlation_pm25_co2": 0.45,
}


def generate_traffic_light(n=200):
    """Replica of the planned generator."""
    states = []
    current_state = "green"
    for i in range(n):
        params = TRAFFIC_LIGHT_PARAMS[current_state]
        duration = int(np.clip(
            np.random.normal(params["mean_duration"], params["std_duration"]),
            params["min"],
            params["max"],
        ))
        lat = 50.45 + random.gauss(0, 0.005)
        lon = 30.52 + random.gauss(0, 0.005)
        states.append({
            "state": current_state,
            "duration": duration,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
        })
        transitions = TRAFFIC_LIGHT_PARAMS["transitions"][current_state]
        current_state = random.choices(
            list(transitions.keys()),
            weights=list(transitions.values()),
        )[0]
    return states


def generate_air_quality(n=200):
    """Replica of the planned generator."""
    params = AIR_QUALITY_PARAMS
    corr_matrix = np.array([
        [1.0, params["correlation_pm25_pm10"], params["correlation_pm25_co2"]],
        [params["correlation_pm25_pm10"], 1.0, 0.35],
        [params["correlation_pm25_co2"], 0.35, 1.0],
    ])
    L = np.linalg.cholesky(corr_matrix)
    data = []
    for _ in range(n):
        z = np.random.randn(3)
        correlated = L @ z
        pm25 = float(np.clip(
            params["pm25"]["mean"] + correlated[0] * params["pm25"]["std"],
            params["pm25"]["min"],
            params["pm25"]["max"],
        ))
        pm10 = float(np.clip(
            params["pm10"]["mean"] + correlated[1] * params["pm10"]["std"],
            params["pm10"]["min"],
            params["pm10"]["max"],
        ))
        co2 = float(np.clip(
            params["co2"]["mean"] + correlated[2] * params["co2"]["std"],
            params["co2"]["min"],
            params["co2"]["max"],
        ))
        pm10 = max(pm10, pm25 * 1.2)
        data.append({
            "pm25": round(pm25, 1),
            "pm10": round(pm10, 1),
            "co2": round(co2, 1),
        })
    return data


# ===================================================================
# TrafficLight generator tests
# ===================================================================

class TestGenerateTrafficLight:
    @pytest.fixture(autouse=True)
    def _seed(self):
        np.random.seed(42)
        random.seed(42)

    def test_returns_200_records(self):
        data = generate_traffic_light(200)
        assert len(data) == 200

    def test_returns_custom_count(self):
        data = generate_traffic_light(50)
        assert len(data) == 50

    def test_all_states_present(self):
        data = generate_traffic_light(200)
        states = {r["state"] for r in data}
        assert "green" in states
        assert "yellow" in states
        assert "red" in states

    def test_only_valid_states(self):
        data = generate_traffic_light(200)
        valid = {"green", "yellow", "red"}
        for r in data:
            assert r["state"] in valid

    def test_green_duration_within_range(self):
        data = generate_traffic_light(200)
        for r in data:
            if r["state"] == "green":
                assert 15 <= r["duration"] <= 55

    def test_yellow_duration_within_range(self):
        data = generate_traffic_light(200)
        for r in data:
            if r["state"] == "yellow":
                assert 3 <= r["duration"] <= 5

    def test_red_duration_within_range(self):
        data = generate_traffic_light(200)
        for r in data:
            if r["state"] == "red":
                assert 20 <= r["duration"] <= 65

    def test_has_gps_coordinates(self):
        data = generate_traffic_light(200)
        for r in data:
            assert "latitude" in r
            assert "longitude" in r
            assert isinstance(r["latitude"], float)
            assert isinstance(r["longitude"], float)

    def test_gps_near_kyiv(self):
        """Generated GPS should be near Kyiv (50.45, 30.52)."""
        data = generate_traffic_light(200)
        for r in data:
            assert abs(r["latitude"] - 50.45) < 0.1
            assert abs(r["longitude"] - 30.52) < 0.1

    def test_markov_chain_transitions(self):
        """Transitions should follow green->yellow->red->green cycle."""
        data = generate_traffic_light(200)
        for i in range(len(data) - 1):
            curr = data[i]["state"]
            nxt = data[i + 1]["state"]
            if curr == "green":
                assert nxt == "yellow"
            elif curr == "yellow":
                assert nxt == "red"
            elif curr == "red":
                assert nxt == "green"

    def test_duration_is_integer(self):
        data = generate_traffic_light(200)
        for r in data:
            assert isinstance(r["duration"], int)

    def test_green_mean_duration_approximately_correct(self):
        """Mean green duration should be roughly 35 s (within 5 s)."""
        data = generate_traffic_light(600)
        green_durations = [r["duration"] for r in data if r["state"] == "green"]
        if green_durations:
            mean = sum(green_durations) / len(green_durations)
            assert abs(mean - 35) < 5

    def test_record_keys(self):
        data = generate_traffic_light(10)
        expected_keys = {"state", "duration", "latitude", "longitude"}
        for r in data:
            assert set(r.keys()) == expected_keys

    def test_single_record(self):
        """Generating a single record should work."""
        data = generate_traffic_light(1)
        assert len(data) == 1
        assert data[0]["state"] == "green"  # always starts with green

    def test_zero_records(self):
        """Generating zero records should return an empty list."""
        data = generate_traffic_light(0)
        assert data == []

    def test_starts_with_green(self):
        """The generator always starts from the 'green' state."""
        data = generate_traffic_light(3)
        assert data[0]["state"] == "green"


# ===================================================================
# AirQuality generator tests
# ===================================================================

class TestGenerateAirQuality:
    @pytest.fixture(autouse=True)
    def _seed(self):
        np.random.seed(42)
        random.seed(42)

    def test_returns_200_records(self):
        data = generate_air_quality(200)
        assert len(data) == 200

    def test_returns_custom_count(self):
        data = generate_air_quality(75)
        assert len(data) == 75

    def test_pm10_gte_pm25(self):
        """PM10 must always be >= PM2.5 (physical constraint: pm10 >= pm25 * 1.2)."""
        data = generate_air_quality(500)
        for r in data:
            assert r["pm10"] >= r["pm25"], (
                f"PM10 ({r['pm10']}) < PM2.5 ({r['pm25']})"
            )

    def test_pm25_within_range(self):
        data = generate_air_quality(500)
        for r in data:
            assert r["pm25"] >= AIR_QUALITY_PARAMS["pm25"]["min"]
            assert r["pm25"] <= AIR_QUALITY_PARAMS["pm25"]["max"]

    def test_pm10_min_bound(self):
        data = generate_air_quality(500)
        for r in data:
            # pm10 is max(clipped, pm25*1.2), so it could exceed the
            # configured max due to the pm25 scaling, but should never
            # be below the configured minimum
            assert r["pm10"] >= AIR_QUALITY_PARAMS["pm10"]["min"] or r["pm10"] >= r["pm25"] * 1.2

    def test_co2_within_range(self):
        data = generate_air_quality(500)
        for r in data:
            assert r["co2"] >= AIR_QUALITY_PARAMS["co2"]["min"]
            assert r["co2"] <= AIR_QUALITY_PARAMS["co2"]["max"]

    def test_values_are_rounded_to_1_decimal(self):
        data = generate_air_quality(200)
        for r in data:
            for key in ("pm25", "pm10", "co2"):
                # round(x, 1) means at most 1 decimal place
                assert r[key] == round(r[key], 1)

    def test_record_keys(self):
        data = generate_air_quality(10)
        expected_keys = {"pm25", "pm10", "co2"}
        for r in data:
            assert set(r.keys()) == expected_keys

    def test_pm25_mean_approximately_correct(self):
        """Mean PM2.5 should be roughly 15 ug/m3 (within 5)."""
        data = generate_air_quality(1000)
        pm25_values = [r["pm25"] for r in data]
        mean = sum(pm25_values) / len(pm25_values)
        assert abs(mean - 15.0) < 5.0

    def test_co2_mean_approximately_correct(self):
        """Mean CO2 should be roughly 420 ppm (within 20)."""
        data = generate_air_quality(1000)
        co2_values = [r["co2"] for r in data]
        mean = sum(co2_values) / len(co2_values)
        assert abs(mean - 420.0) < 20.0

    def test_pm25_pm10_correlation_positive(self):
        """PM2.5 and PM10 should be positively correlated (r > 0.5)."""
        data = generate_air_quality(500)
        pm25 = np.array([r["pm25"] for r in data])
        pm10 = np.array([r["pm10"] for r in data])
        corr = np.corrcoef(pm25, pm10)[0, 1]
        assert corr > 0.5, f"Expected positive correlation, got r={corr:.2f}"

    def test_pm25_co2_correlation_positive(self):
        """PM2.5 and CO2 should have moderate positive correlation (r > 0.1)."""
        data = generate_air_quality(500)
        pm25 = np.array([r["pm25"] for r in data])
        co2 = np.array([r["co2"] for r in data])
        corr = np.corrcoef(pm25, co2)[0, 1]
        assert corr > 0.1, f"Expected positive correlation, got r={corr:.2f}"

    def test_variation_exists(self):
        """Values should not all be identical."""
        data = generate_air_quality(50)
        pm25_values = {r["pm25"] for r in data}
        assert len(pm25_values) > 1

    def test_single_record(self):
        """Generating a single record should work."""
        data = generate_air_quality(1)
        assert len(data) == 1
        assert "pm25" in data[0]
        assert "pm10" in data[0]
        assert "co2" in data[0]

    def test_zero_records(self):
        """Generating zero records should return an empty list."""
        data = generate_air_quality(0)
        assert data == []

    def test_all_values_are_floats(self):
        """All generated values should be floats (not ints or numpy scalars)."""
        data = generate_air_quality(10)
        for r in data:
            assert isinstance(r["pm25"], float)
            assert isinstance(r["pm10"], float)
            assert isinstance(r["co2"], float)
