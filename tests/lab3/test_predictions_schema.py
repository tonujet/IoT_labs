"""
Tests for the 'predictions' database table schema.

Validates that the SQL definition (in structure.sql) contains the expected
columns with correct types.  No running database is needed -- the tests
parse the SQL file directly.
"""
import os
import re
import pytest


# ---------------------------------------------------------------------------
# Locate structure.sql files
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

STRUCTURE_SQL_PATHS = [
    os.path.join(PROJECT_ROOT, "store", "docker", "db", "structure.sql"),
    os.path.join(PROJECT_ROOT, "edge", "docker", "db", "structure.sql"),
    os.path.join(PROJECT_ROOT, "hub", "docker", "db", "structure.sql"),
]


def _read_sql(path: str) -> str:
    """Read a structure.sql file, return its content in lowercase."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().lower()


def _extract_predictions_block(sql: str) -> str:
    """
    Extract the CREATE TABLE predictions (...) block from the full SQL.
    Returns the text between the parentheses (column definitions).
    Returns None if the predictions table is not found.
    """
    match = re.search(
        r"create\s+table\s+predictions\s*\((.*?)\)\s*;",
        sql,
        re.DOTALL,
    )
    if match is None:
        return None
    return match.group(1)


# ===================================================================
# Schema tests -- run against every structure.sql that exists
# ===================================================================

def _existing_sql_paths():
    """Return only the structure.sql paths that actually exist on disk."""
    return [p for p in STRUCTURE_SQL_PATHS if os.path.isfile(p)]


def _sql_paths_with_predictions():
    """Return structure.sql paths that contain the predictions table."""
    paths = []
    for p in _existing_sql_paths():
        sql = _read_sql(p)
        if "create table predictions" in sql:
            paths.append(p)
    return paths


@pytest.fixture(params=_sql_paths_with_predictions() or [pytest.param("none", marks=pytest.mark.skip(reason="No structure.sql contains predictions table yet"))], ids=lambda p: os.path.basename(os.path.dirname(os.path.dirname(p))) if isinstance(p, str) and os.path.isfile(p) else "skipped")
def predictions_block(request):
    """Fixture that yields the predictions CREATE TABLE block for each SQL file."""
    if not os.path.isfile(request.param):
        pytest.skip("No structure.sql with predictions table found")
    sql = _read_sql(request.param)
    block = _extract_predictions_block(sql)
    if block is None:
        pytest.skip("predictions table not found in this structure.sql")
    return block


class TestPredictionsTableExists:
    """Verify that at least one structure.sql defines the predictions table."""

    def test_at_least_one_structure_sql_exists(self):
        existing = _existing_sql_paths()
        assert len(existing) > 0, "No structure.sql files found"

    def test_predictions_table_defined(self):
        """At least one structure.sql should contain CREATE TABLE predictions."""
        found = False
        for path in _existing_sql_paths():
            sql = _read_sql(path)
            if "create table predictions" in sql:
                found = True
                break
        if not found:
            pytest.skip(
                "No structure.sql contains CREATE TABLE predictions yet "
                "(Lab 3 not implemented)"
            )
        assert found


class TestPredictionsColumns:
    """Validate individual columns of the predictions table."""

    def test_has_id_column(self, predictions_block):
        assert "id" in predictions_block

    def test_id_is_serial_primary_key(self, predictions_block):
        assert "serial" in predictions_block
        assert "primary key" in predictions_block

    def test_has_field_name_column(self, predictions_block):
        assert "field_name" in predictions_block

    def test_field_name_is_varchar(self, predictions_block):
        """field_name should be VARCHAR (any length)."""
        pattern = r"field_name\s+varchar"
        assert re.search(pattern, predictions_block), (
            "field_name should be VARCHAR"
        )

    def test_has_predicted_value_column(self, predictions_block):
        assert "predicted_value" in predictions_block

    def test_predicted_value_is_float(self, predictions_block):
        """predicted_value should be FLOAT (or DOUBLE PRECISION / REAL)."""
        pattern = r"predicted_value\s+(float|double precision|real|numeric)"
        assert re.search(pattern, predictions_block), (
            "predicted_value should be FLOAT"
        )

    def test_has_prediction_timestamp_column(self, predictions_block):
        assert "prediction_timestamp" in predictions_block

    def test_prediction_timestamp_is_timestamp(self, predictions_block):
        pattern = r"prediction_timestamp\s+timestamp"
        assert re.search(pattern, predictions_block), (
            "prediction_timestamp should be TIMESTAMP"
        )

    def test_has_created_at_column(self, predictions_block):
        assert "created_at" in predictions_block

    def test_created_at_is_timestamp(self, predictions_block):
        pattern = r"created_at\s+timestamp"
        assert re.search(pattern, predictions_block), (
            "created_at should be TIMESTAMP"
        )

    def test_has_model_name_column(self, predictions_block):
        assert "model_name" in predictions_block

    def test_model_name_is_varchar(self, predictions_block):
        pattern = r"model_name\s+varchar"
        assert re.search(pattern, predictions_block), (
            "model_name should be VARCHAR"
        )

    def test_has_mae_column(self, predictions_block):
        assert "mae" in predictions_block

    def test_mae_is_float(self, predictions_block):
        pattern = r"\bmae\s+(float|double precision|real|numeric)"
        assert re.search(pattern, predictions_block), (
            "mae should be FLOAT"
        )

    def test_has_rmse_column(self, predictions_block):
        assert "rmse" in predictions_block

    def test_rmse_is_float(self, predictions_block):
        pattern = r"\brmse\s+(float|double precision|real|numeric)"
        assert re.search(pattern, predictions_block), (
            "rmse should be FLOAT"
        )

    def test_field_name_is_not_null(self, predictions_block):
        pattern = r"field_name\s+varchar\(\d+\)\s+not\s+null"
        assert re.search(pattern, predictions_block), (
            "field_name should be NOT NULL"
        )

    def test_predicted_value_is_not_null(self, predictions_block):
        pattern = r"predicted_value\s+(float|double precision|real|numeric)\s+not\s+null"
        assert re.search(pattern, predictions_block), (
            "predicted_value should be NOT NULL"
        )

    def test_prediction_timestamp_is_not_null(self, predictions_block):
        pattern = r"prediction_timestamp\s+timestamp\s+not\s+null"
        assert re.search(pattern, predictions_block), (
            "prediction_timestamp should be NOT NULL"
        )


class TestAllRequiredColumns:
    """Verify all required columns are present in one check."""

    def test_all_columns_present(self, predictions_block):
        required_columns = [
            "id",
            "field_name",
            "predicted_value",
            "prediction_timestamp",
            "created_at",
            "model_name",
            "mae",
            "rmse",
        ]
        for col in required_columns:
            assert col in predictions_block, (
                f"Required column '{col}' missing from predictions table"
            )
