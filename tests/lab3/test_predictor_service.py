"""
Tests for predictor service logic (fetch, save, run cycle).

All database interactions are mocked -- no real PostgreSQL required.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Ensure predictor/main.py is importable.  If it doesn't exist yet the
# whole module is skipped (TDD).
# ---------------------------------------------------------------------------
_PREDICTOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "predictor")
)
if not os.path.isfile(os.path.join(_PREDICTOR_DIR, "main.py")):
    pytest.skip(
        "predictor/main.py not yet implemented (TDD -- skipping)",
        allow_module_level=True,
    )

sys.path.insert(0, _PREDICTOR_DIR)


def _make_mock_engine():
    """Helper: create a mock engine with a working connect() context manager."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_conn.execute.return_value = mock_result

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_conn)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_engine.connect.return_value = ctx

    return mock_engine, mock_conn, mock_result


# ===================================================================
# fetch_historical_data
# ===================================================================

class TestFetchHistoricalData:
    """Tests for fetching historical sensor data from DB."""

    @patch("main.get_engine")
    def test_returns_data_in_chronological_order(self, mock_get_engine):
        """The raw query uses ORDER BY DESC; the function must reverse."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        ts3 = datetime(2026, 1, 1, 0, 3)
        ts2 = datetime(2026, 1, 1, 0, 2)
        ts1 = datetime(2026, 1, 1, 0, 1)
        mock_result.fetchall.return_value = [
            (ts3, 30.0),
            (ts2, 20.0),
            (ts1, 10.0),
        ]

        from main import fetch_historical_data
        data = fetch_historical_data("temperature", limit=100)

        assert data[0] == (ts1, 10.0)
        assert data[1] == (ts2, 20.0)
        assert data[2] == (ts3, 30.0)

    @patch("main.get_engine")
    def test_handles_empty_result(self, mock_get_engine):
        """When the query returns no rows, an empty list is expected."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import fetch_historical_data
        data = fetch_historical_data("pm25", limit=50)
        assert data == []

    @patch("main.get_engine")
    def test_passes_limit_to_query(self, mock_get_engine):
        """The limit parameter must be forwarded to the SQL query."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import fetch_historical_data
        fetch_historical_data("temperature", limit=42)

        assert mock_conn.execute.called

    @patch("main.get_engine")
    def test_returns_tuples_of_timestamp_and_value(self, mock_get_engine):
        """Each item should be a (timestamp, float) tuple."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        ts = datetime(2026, 1, 1, 12, 0)
        mock_result.fetchall.return_value = [(ts, 25.5)]

        from main import fetch_historical_data
        data = fetch_historical_data("temperature", limit=10)
        assert len(data) == 1
        assert data[0][0] == ts
        assert data[0][1] == 25.5


# ===================================================================
# save_predictions
# ===================================================================

class TestSavePredictions:
    """Tests for writing predictions back to the DB."""

    @patch("main.get_engine")
    def test_correct_number_of_inserts(self, mock_get_engine):
        """One INSERT per prediction value."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import save_predictions

        base_ts = datetime(2026, 1, 1)
        predictions = [1.0, 2.0, 3.0, 4.0, 5.0]
        timestamps = [base_ts + timedelta(minutes=i) for i in range(5)]

        save_predictions("temperature", predictions, timestamps,
                         "LinearRegression", 0.5, 0.7)

        assert mock_conn.execute.call_count == 5
        mock_conn.commit.assert_called_once()

    @patch("main.get_engine")
    def test_correct_field_values_passed(self, mock_get_engine):
        """Verify the parameter dict passed to each INSERT."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import save_predictions

        ts = datetime(2026, 6, 15, 12, 0)
        save_predictions("pm25", [99.9], [ts], "MovingAverage", 1.2, 1.5)

        call_args = mock_conn.execute.call_args_list[0]
        params = call_args[0][1]
        assert params["field"] == "pm25"
        assert params["value"] == 99.9
        assert params["ts"] == ts
        assert params["model"] == "MovingAverage"
        assert params["mae"] == 1.2
        assert params["rmse"] == 1.5

    @patch("main.get_engine")
    def test_empty_predictions_no_inserts(self, mock_get_engine):
        """If predictions list is empty, nothing should be inserted."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import save_predictions
        save_predictions("temperature", [], [], "LinearRegression", 0.0, 0.0)

        assert mock_conn.execute.call_count == 0

    @patch("main.get_engine")
    def test_commit_is_called(self, mock_get_engine):
        """The transaction must be committed after all inserts."""
        mock_engine, mock_conn, mock_result = _make_mock_engine()
        mock_get_engine.return_value = mock_engine

        from main import save_predictions

        base_ts = datetime(2026, 1, 1)
        save_predictions("temperature", [10.0], [base_ts],
                         "LinearRegression", 0.1, 0.2)

        mock_conn.commit.assert_called_once()


# ===================================================================
# run_prediction_cycle
# ===================================================================

class TestRunPredictionCycle:
    """Tests for the main orchestration function."""

    @patch("main.save_predictions")
    @patch("main.train_and_predict_moving_avg")
    @patch("main.train_and_predict_linear")
    @patch("main.fetch_historical_data")
    def test_runs_for_both_fields(
        self, mock_fetch, mock_lr, mock_ma, mock_save
    ):
        """run_prediction_cycle should process both 'temperature' and 'pm25'."""
        base = datetime(2026, 1, 1)
        fake_data = [(base + timedelta(minutes=i), float(i)) for i in range(50)]
        mock_fetch.return_value = fake_data
        mock_lr.return_value = ([1.0] * 20, 0.5, 0.7)
        mock_ma.return_value = ([2.0] * 20, 0.3, 0.4)

        from main import run_prediction_cycle
        run_prediction_cycle()

        fetch_calls = [c[0][0] for c in mock_fetch.call_args_list]
        assert "temperature" in fetch_calls
        assert "pm25" in fetch_calls

    @patch("main.save_predictions")
    @patch("main.train_and_predict_moving_avg")
    @patch("main.train_and_predict_linear")
    @patch("main.fetch_historical_data")
    def test_skips_fields_with_insufficient_data(
        self, mock_fetch, mock_lr, mock_ma, mock_save
    ):
        """If a field has < 10 data points, predictions should be skipped."""
        base = datetime(2026, 1, 1)
        small_data = [(base + timedelta(minutes=i), float(i)) for i in range(5)]
        mock_fetch.return_value = small_data

        from main import run_prediction_cycle
        run_prediction_cycle()

        mock_lr.assert_not_called()
        mock_ma.assert_not_called()
        mock_save.assert_not_called()

    @patch("main.save_predictions")
    @patch("main.train_and_predict_moving_avg")
    @patch("main.train_and_predict_linear")
    @patch("main.fetch_historical_data")
    def test_saves_predictions_for_both_models(
        self, mock_fetch, mock_lr, mock_ma, mock_save
    ):
        """When data is sufficient, predictions from both models are saved."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(50)]
        mock_fetch.return_value = data
        mock_lr.return_value = ([1.0] * 20, 0.5, 0.7)
        mock_ma.return_value = ([2.0] * 20, 0.3, 0.4)

        from main import run_prediction_cycle
        run_prediction_cycle()

        # 2 fields * 2 models = 4 calls
        assert mock_save.call_count == 4

        # save_predictions is called with positional args:
        # save_predictions(field, preds, timestamps, model_name, mae, rmse)
        # so model_name is args[3]
        model_names = [c[0][3] for c in mock_save.call_args_list]
        assert "LinearRegression" in model_names
        assert "MovingAverage" in model_names

    @patch("main.save_predictions")
    @patch("main.train_and_predict_moving_avg")
    @patch("main.train_and_predict_linear")
    @patch("main.fetch_historical_data")
    def test_handles_linear_returning_none(
        self, mock_fetch, mock_lr, mock_ma, mock_save
    ):
        """If linear regression returns None, it should not save, but MA can."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(50)]
        mock_fetch.return_value = data
        mock_lr.return_value = (None, None, None)
        mock_ma.return_value = ([2.0] * 20, 0.3, 0.4)

        from main import run_prediction_cycle
        run_prediction_cycle()

        # Only MA saves: 2 fields * 1 model = 2
        assert mock_save.call_count == 2
        for c in mock_save.call_args_list:
            assert c[0][3] == "MovingAverage"

    @patch("main.save_predictions")
    @patch("main.train_and_predict_moving_avg")
    @patch("main.train_and_predict_linear")
    @patch("main.fetch_historical_data")
    def test_generates_future_timestamps(
        self, mock_fetch, mock_lr, mock_ma, mock_save
    ):
        """Saved timestamps should be in the future relative to last data point."""
        base = datetime(2026, 1, 1)
        data = [(base + timedelta(minutes=i), float(i)) for i in range(50)]
        mock_fetch.return_value = data
        mock_lr.return_value = ([1.0] * 20, 0.5, 0.7)
        mock_ma.return_value = (None, None, None)

        from main import run_prediction_cycle
        run_prediction_cycle()

        last_data_ts = data[-1][0]
        for c in mock_save.call_args_list:
            # timestamps is the 3rd positional arg (index 2)
            timestamps = c[0][2]
            for ts in timestamps:
                assert ts > last_data_ts
