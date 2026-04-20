"""
Tests for Grafana provisioning YAML configuration files.

Validates that the datasource and dashboard provider configs are
well-formed and contain the correct values for the IoT stack.

These tests are skipped if the Grafana provisioning files do not
exist yet (Lab 3 implementation not started).
"""
import os
import pytest
import yaml


# ---------------------------------------------------------------------------
# Paths to provisioning files (relative to project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
GRAFANA_DIR = os.path.join(
    PROJECT_ROOT, "edge", "docker", "grafana"
)
DATASOURCE_PATH = os.path.join(
    GRAFANA_DIR, "provisioning", "datasources", "postgres.yaml"
)
DASHBOARD_PROVIDER_PATH = os.path.join(
    GRAFANA_DIR, "provisioning", "dashboards", "dashboards.yaml"
)

# Skip the entire module if grafana provisioning directory doesn't exist yet
if not os.path.isdir(GRAFANA_DIR):
    pytest.skip(
        "Grafana provisioning directory not yet created (Lab 3 -- skipping)",
        allow_module_level=True,
    )


# ===================================================================
# Datasource YAML
# ===================================================================

class TestDatasourceConfig:
    """Validate the Grafana PostgreSQL datasource provisioning file."""

    def test_file_exists(self):
        assert os.path.isfile(DATASOURCE_PATH), (
            f"Datasource config not found at {DATASOURCE_PATH}"
        )

    def test_valid_yaml(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_api_version(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "apiVersion" in data

    def test_has_datasources_list(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "datasources" in data
        assert isinstance(data["datasources"], list)
        assert len(data["datasources"]) >= 1

    def test_datasource_type_is_postgres(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert ds["type"] == "postgres"

    def test_datasource_url_points_to_postgres_db(self):
        """The URL should reference the Docker service name and port."""
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert "postgres_db" in ds["url"]
        assert "5432" in ds["url"]

    def test_datasource_database_name(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert ds["database"] == "test_db"

    def test_datasource_user(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert ds["user"] == "user"

    def test_datasource_password_in_secure_json(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert "secureJsonData" in ds
        assert ds["secureJsonData"].get("password") == "pass"

    def test_ssl_mode_disabled(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        json_data = ds.get("jsonData", {})
        assert json_data.get("sslmode") == "disable"

    def test_is_default_datasource(self):
        with open(DATASOURCE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert ds.get("isDefault") is True


# ===================================================================
# Dashboard provider YAML
# ===================================================================

class TestDashboardProviderConfig:
    """Validate the Grafana dashboard provider provisioning file."""

    def test_file_exists(self):
        assert os.path.isfile(DASHBOARD_PROVIDER_PATH), (
            f"Dashboard provider config not found at {DASHBOARD_PROVIDER_PATH}"
        )

    def test_valid_yaml(self):
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_api_version(self):
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "apiVersion" in data

    def test_has_providers_list(self):
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "providers" in data
        assert isinstance(data["providers"], list)
        assert len(data["providers"]) >= 1

    def test_provider_type_is_file(self):
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        provider = data["providers"][0]
        assert provider["type"] == "file"

    def test_provider_path_points_to_dashboards_dir(self):
        """The path should be the container-internal dashboards directory."""
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        provider = data["providers"][0]
        options_path = provider.get("options", {}).get("path", "")
        assert "/var/lib/grafana/dashboards" in options_path

    def test_provider_has_name(self):
        with open(DASHBOARD_PROVIDER_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        provider = data["providers"][0]
        assert "name" in provider
        assert len(provider["name"]) > 0
