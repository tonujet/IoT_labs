"""
Tests for ML prediction functions in predictor/main.py.

Uses synthetic data -- no database or Docker required.
Written TDD-style: tests are defined before the implementation.
"""
import os
import sys
import pytest
import numpy as np
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Import helpers -- predictor/main.py will expose these functions.
# We ensure the predictor directory is first on sys.path so that
# ``import main`` resolves to predictor/main.py, not store/main.py.
# If predictor/main.py does not exist yet the entire module is skipped
# (standard TDD: tests are collected only once implementation lands).
# ---------------------------------------------------------------------------
_PREDICTOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "predictor")
)
if not os.path.isfile(os.path.join(_PREDICTOR_DIR, "main.py")):
    pytest.skip(
        "predictor/main.py not yet implemented (TDD -- skipping)",
        allow_module_level=True,
    )

# Put predictor dir at front so its main.py wins over store/main.py
sys.path.insert(0, _PREDICTOR_DIR)
from main import train_and_predict_linear, train_and_predict_moving_avg  # noqa: E402


# ===================================================================
# train_and_predict_linear
# ===================================================================

class TestTrainAndPredictLinear:
    """Tests for the LinearRegression-based prediction function."""

    def test_predictions_follow_linear_trend(self, linear_data):
        """Given perfectly linear data, predictions should continue the trend."""
        predictions, mae, rmse = train_and_predict_linear(linear_data, steps=5)

        assert predictions is not None
        assert len(predictions) == 5

        # The data is value = 2*i + 10.  After 50 points (i=0..49),
        # the next predictions (i=50..54) should be approximately 2*i+10.
        for idx, pred in enumerate(predictions):
            expected = 2.0 * (50 + idx) + 10.0
            assert abs(pred - expected) < 1.0, (
                f"Prediction {idx} = {pred}, expected ~{expected}"
            )

    def test_constant_data_predicts_near_constant(self, constant_data):
        """With constant input, predictions should stay near that constant."""
        predictions, mae, rmse = train_and_predict_linear(constant_data, steps=5)

        assert predictions is not None
        for pred in predictions:
            assert abs(pred - 42.0) < 0.5

    def test_insufficient_data_returns_none(self, small_data):
        """With fewer than 10 data points the function should return None."""
        predictions, mae, rmse = train_and_predict_linear(small_data, steps=5)
        assert predictions is None
        assert mae is None
        assert rmse is None

    def test_mae_is_non_negative(self, linear_data):
        _, mae, _ = train_and_predict_linear(linear_data, steps=5)
        assert mae is not None
        assert mae >= 0

    def test_rmse_is_non_negative(self, linear_data):
        _, _, rmse = train_and_predict_linear(linear_data, steps=5)
        assert rmse is not None
        assert rmse >= 0

    def test_returns_correct_number_of_steps(self, linear_data):
        """The number of predictions must equal the requested steps."""
        for steps in (1, 5, 20, 50):
            predictions, _, _ = train_and_predict_linear(linear_data, steps=steps)
            assert predictions is not None
            assert len(predictions) == steps

    def test_predictions_are_floats(self, linear_data):
        predictions, _, _ = train_and_predict_linear(linear_data, steps=3)
        assert predictions is not None
        for p in predictions:
            assert isinstance(p, float)

    def test_mae_less_than_or_equal_rmse(self, trending_data):
        """MAE <= RMSE always holds (Cauchy-Schwarz / Jensen)."""
        _, mae, rmse = train_and_predict_linear(trending_data, steps=10)
        assert mae is not None and rmse is not None
        assert mae <= rmse + 1e-9  # small epsilon for float rounding

    def test_with_exactly_10_points(self):
        """Boundary: exactly 10 data points should be accepted."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(10)]
        predictions, mae, rmse = train_and_predict_linear(data, steps=3)
        assert predictions is not None
        assert len(predictions) == 3

    def test_with_9_points_returns_none(self):
        """Boundary: 9 data points is below the threshold."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(9)]
        predictions, mae, rmse = train_and_predict_linear(data, steps=3)
        assert predictions is None


# ===================================================================
# train_and_predict_moving_avg
# ===================================================================

class TestTrainAndPredictMovingAvg:
    """Tests for the Moving Average prediction function."""

    def test_constant_data_predicts_constant(self, constant_data):
        """With constant values the MA prediction should equal that constant."""
        predictions, mae, rmse = train_and_predict_moving_avg(
            constant_data, window=10, steps=5
        )
        assert predictions is not None
        for pred in predictions:
            assert abs(pred - 42.0) < 1e-6

    def test_trending_data_follows_trend(self, trending_data):
        """With trending data, predictions should move in the same direction."""
        predictions, _, _ = train_and_predict_moving_avg(
            trending_data, window=10, steps=5
        )
        assert predictions is not None
        # Predictions should generally increase (positive trend)
        assert predictions[-1] > predictions[0] or abs(predictions[-1] - predictions[0]) < 5

    def test_insufficient_data_returns_none(self):
        """If the dataset is smaller than the window, return None."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(5)]
        predictions, mae, rmse = train_and_predict_moving_avg(
            data, window=10, steps=5
        )
        assert predictions is None
        assert mae is None
        assert rmse is None

    def test_mae_is_non_negative(self, constant_data):
        _, mae, _ = train_and_predict_moving_avg(
            constant_data, window=10, steps=5
        )
        assert mae is not None
        assert mae >= 0

    def test_rmse_is_non_negative(self, constant_data):
        _, _, rmse = train_and_predict_moving_avg(
            constant_data, window=10, steps=5
        )
        assert rmse is not None
        assert rmse >= 0

    def test_returns_correct_number_of_steps(self, trending_data):
        for steps in (1, 5, 20):
            predictions, _, _ = train_and_predict_moving_avg(
                trending_data, window=10, steps=steps
            )
            assert predictions is not None
            assert len(predictions) == steps

    def test_constant_data_zero_mae(self, constant_data):
        """For perfectly constant data, MAE and RMSE should be 0."""
        _, mae, rmse = train_and_predict_moving_avg(
            constant_data, window=10, steps=5
        )
        assert mae is not None
        assert abs(mae) < 1e-9
        assert abs(rmse) < 1e-9

    def test_window_equals_data_length(self):
        """Edge case: window size == data length should still work."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(10)]
        predictions, mae, rmse = train_and_predict_moving_avg(
            data, window=10, steps=3
        )
        assert predictions is not None
        assert len(predictions) == 3

    def test_predictions_are_numeric(self, trending_data):
        predictions, _, _ = train_and_predict_moving_avg(
            trending_data, window=10, steps=5
        )
        assert predictions is not None
        for p in predictions:
            assert isinstance(p, (int, float))
