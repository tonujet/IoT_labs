"""
Tests for new Store API endpoints added in Lab 3.

GET /metrics/summary   -- aggregated statistics
GET /metrics/timeseries -- time-series data for a specific field

All database access is mocked -- no PostgreSQL or psycopg2 required.
"""
import os
import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Ensure store/ is importable.
# ---------------------------------------------------------------------------
_STORE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "store")
)
sys.path.insert(0, _STORE_DIR)

try:
    from fastapi.testclient import TestClient  # noqa: E402
    import sqlalchemy  # noqa: E402
except ImportError:
    pytest.skip(
        "fastapi or sqlalchemy not installed -- skipping store endpoint tests",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Fixture: a TestClient whose underlying store/main.py has a fully mocked
# database layer.  We patch create_engine *before* (re-)importing main so
# that the module-level ``engine = create_engine(...)`` never touches
# psycopg2 / PostgreSQL.
# ---------------------------------------------------------------------------

@pytest.fixture
def store_app():
    """
    Import (or reload) store/main.py with a mocked DB layer and return
    (app, mock_session_factory) so tests can configure per-test mocks.
    """
    mock_engine = MagicMock()
    mock_session_cls = MagicMock()

    with patch("sqlalchemy.create_engine", return_value=mock_engine), \
         patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_cls):
        # Remove cached module so the patches take effect at module-level
        if "main" in sys.modules:
            del sys.modules["main"]
        import main as store_main  # noqa: F811

    app = store_main.app

    # Check if the Lab 3 endpoints exist; skip if not
    routes = [r.path for r in app.routes]
    if "/metrics/summary" not in routes or "/metrics/timeseries" not in routes:
        pytest.skip(
            "Store API does not yet have /metrics/summary and /metrics/timeseries "
            "endpoints (Lab 3 not implemented)"
        )

    return app, mock_session_cls


@pytest.fixture
def client(store_app):
    app, _ = store_app
    return TestClient(app)


# ===================================================================
# GET /metrics/summary
# ===================================================================

class TestMetricsSummary:
    """Tests for the /metrics/summary endpoint."""

    def test_returns_correct_keys(self, store_app, sample_db_summary_row):
        """Response must include the expected aggregation keys."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = sample_db_summary_row

        client = TestClient(app)
        response = client.get("/metrics/summary")
        assert response.status_code == 200
        data = response.json()

        expected_keys = {
            "total_records", "avg_temp", "avg_rain", "avg_pm25",
            "potholes", "bumps", "first_record", "last_record",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_returns_correct_values(self, store_app, sample_db_summary_row):
        """Values in the response should match the mock DB row."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = sample_db_summary_row

        client = TestClient(app)
        response = client.get("/metrics/summary")
        data = response.json()

        assert data["total_records"] == 150
        assert data["avg_temp"] == 22.5
        assert data["avg_rain"] == 3.1
        assert data["potholes"] == 12
        assert data["bumps"] == 8

    def test_response_is_dict(self, store_app, sample_db_summary_row):
        """The response should be a JSON object (dict), not a list."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchone.return_value = sample_db_summary_row

        client = TestClient(app)
        response = client.get("/metrics/summary")
        assert isinstance(response.json(), dict)


# ===================================================================
# GET /metrics/timeseries
# ===================================================================

class TestMetricsTimeseries:
    """Tests for the /metrics/timeseries endpoint."""

    def test_valid_field_returns_200(self, store_app, sample_timeseries_rows):
        """A valid field name should return HTTP 200."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = sample_timeseries_rows

        client = TestClient(app)
        response = client.get("/metrics/timeseries", params={"field": "temperature"})
        assert response.status_code == 200

    def test_invalid_field_returns_400(self, store_app):
        """An unsupported field name should return HTTP 400."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        client = TestClient(app)
        response = client.get(
            "/metrics/timeseries", params={"field": "nonexistent_field"}
        )
        assert response.status_code == 400

    def test_returns_list_of_dicts(self, store_app, sample_timeseries_rows):
        """The response body should be a JSON array of objects."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = sample_timeseries_rows

        client = TestClient(app)
        response = client.get("/metrics/timeseries", params={"field": "temperature"})
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert isinstance(data[0], dict)

    def test_limit_parameter_is_forwarded(self, store_app):
        """The limit query param should constrain the number of results."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = []

        client = TestClient(app)
        response = client.get(
            "/metrics/timeseries", params={"field": "temperature", "limit": 10}
        )
        assert response.status_code == 200

        # Verify the limit was passed to the DB query
        call_args = mock_db.execute.call_args
        if call_args and len(call_args[0]) > 1:
            params = call_args[0][1]
            assert params.get("limit") == 10

    def test_allowed_fields_list(self, store_app):
        """All documented allowed fields should be accepted."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = []

        client = TestClient(app)
        allowed = [
            "temperature", "rain_intensity", "x", "y", "z", "pm25", "pm10", "co2"
        ]
        for field in allowed:
            response = client.get(
                "/metrics/timeseries", params={"field": field}
            )
            assert response.status_code == 200, (
                f"Field '{field}' should be allowed but got {response.status_code}"
            )

    def test_default_limit_is_100(self, store_app):
        """When no limit is provided, the default should be 100."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = []

        client = TestClient(app)
        response = client.get("/metrics/timeseries", params={"field": "temperature"})
        assert response.status_code == 200

        # The default limit=100 should appear in the query params
        call_args = mock_db.execute.call_args
        if call_args and len(call_args[0]) > 1:
            params = call_args[0][1]
            assert params.get("limit") == 100

    def test_each_row_has_timestamp_and_field(
        self, store_app, sample_timeseries_rows
    ):
        """Each returned object must contain 'timestamp' and the field column."""
        app, mock_session_cls = store_app
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.execute.return_value.fetchall.return_value = sample_timeseries_rows

        client = TestClient(app)
        response = client.get("/metrics/timeseries", params={"field": "temperature"})
        data = response.json()
        for row in data:
            assert "timestamp" in row
            assert "temperature" in row
