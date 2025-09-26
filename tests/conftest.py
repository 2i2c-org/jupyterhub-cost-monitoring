import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.stub import Stubber

# Usage and cost data fixtures for test_cost.py


@pytest.fixture(scope="function")
def input_data_usage():
    with open("tests/data/test_data_usage.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def input_data_cost():
    with open("tests/data/test_data_cost.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_hub():
    with open("tests/data/test_output_hub.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_component():
    with open("tests/data/test_output_component.json") as f:
        data = json.load(f)
    return data


# Usage and cost data for test_integration.py


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    """
    Set environment variables for testing.
    """
    monkeypatch.setenv("CLUSTER_NAME", "test-cluster")


@pytest.fixture(scope="function", params=["compute", "home_storage"])
def mock_usage_response(request, env_vars):
    """
    Mock Prometheus response for compute and home storage components.
    """
    with patch("src.jupyterhub_cost_monitoring.query_usage.requests.get") as mock_get:
        mock_response = MagicMock()
        with open(f"tests/data/test_data_usage_{request.param}.json") as f:
            mock_response.json.return_value = json.load(f)
        mock_get.return_value = mock_response
        mock_get.test_param = request.param
        yield mock_get


@pytest.fixture(scope="function")
def mock_ce(env_vars):
    """
    Mock multiple responses from the AWS Cost Explorer client to validate cost logic of `query_total_costs_per_user` function in `query_cost_aws` submodule.

    Query parameters used to generate json test data files:

    ```
    {
        "TimePeriod": {"Start": "2025-09-01", "End": "2025-09-03"},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        "Filter": base_filter/home_storage_filter/core_filter,
    }
    ```
    """
    aws_ce_client = boto3.client(
        "ce",
        region_name="us-west-2",
        aws_access_key_id="fake-key",
        aws_secret_access_key="fake-secret",
        aws_session_token="fake-token",
    )  # Use fake credentials, otherwise boto3 will use real ones from your environment
    stubber = Stubber(aws_ce_client)
    for c in ["all", "home_storage", "core"]:
        with open(f"tests/data/test_data_cost_component_{c}.json") as f:
            response = json.load(f)
        stubber.add_response("get_cost_and_usage", response)
    with stubber:
        with patch(
            "src.jupyterhub_cost_monitoring.query_cost_aws.aws_ce_client", aws_ce_client
        ):
            yield aws_ce_client


# Date-specific fixtures for date_utils tests


@pytest.fixture
def sample_utc_datetime():
    """Sample UTC datetime for testing."""
    return datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)


@pytest.fixture
def sample_date_range():
    """Sample DateRange for testing."""
    from src.jupyterhub_cost_monitoring.date_utils import DateRange

    start = datetime(2025, 9, 1, tzinfo=timezone.utc)
    end = datetime(2025, 9, 3, tzinfo=timezone.utc)
    return DateRange(start_date=start, end_date=end)


@pytest.fixture
def mock_current_time():
    """Mock current time for consistent testing."""
    return datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def timezone_test_cases():
    """Test cases for different timezone conversions."""
    return [
        # (input_string, expected_utc_datetime)
        ("2024-01-15", datetime(2024, 1, 15, tzinfo=timezone.utc)),
        (
            "2024-01-15T10:00:00-05:00",
            datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15T18:00:00+09:00",
            datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
        ),
        (
            "2024-01-15T12:00:00+00:00",
            datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def date_validation_test_cases():
    """Test cases for date validation scenarios."""
    base_time = datetime(2024, 2, 15, tzinfo=timezone.utc)
    return {
        "current_time": base_time,
        "future_date": "2024-03-01",  # Future end date
        "past_start": "2024-02-16",  # Start date >= current time
        "valid_range": ("2024-01-01", "2024-02-01"),
    }
