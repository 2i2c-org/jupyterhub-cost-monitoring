import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import boto3
import pytest
from botocore.stub import Stubber

os.environ["CLUSTER_NAME"] = "test-cluster"

from src.jupyterhub_cost_monitoring.query_usage import _calculate_daily_cost_factors

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


@pytest.fixture(scope="function")
def output_cost_per_user():
    """
    Output to assert against query_total_costs_per_user function.
    """
    with open("tests/data/test_output_cost_per_user.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_cost_per_group():
    """
    Output to assert against query_total_costs_per_group function.
    """
    with open("tests/data/test_output_cost_per_group.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    """
    Set environment variables for testing.
    """
    # Fake AWS credentials for boto3 client
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "fake-secret")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "fake-token")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.fixture(scope="function")
def mock_prometheus_usage(request):
    """
    Mock Prometheus usage data for compute and home storage components.
    """
    patch_target = "src.jupyterhub_cost_monitoring.query_usage.query_usage"

    param = getattr(request, "param", None)
    if param is not None:
        components = request.param if isinstance(param, list) else [param]

        json_data_map = {}
        for comp in components:
            filename = f"tests/data/test_data_usage_{comp}.json"
            try:
                with open(filename) as f:
                    json_data_map[comp] = json.load(f)
            except FileNotFoundError:
                raise RuntimeError(f"Test data file not found: {filename}")

    def side_effect_func(*args, **kwargs):
        component_name = kwargs.get("component_name")
        if component_name is None:
            all_data = []
            for comp_data in json_data_map.values():
                if isinstance(comp_data, list):
                    all_data.extend(comp_data)
                else:
                    all_data.append(comp_data)
            return all_data
        if component_name not in json_data_map:
            raise ValueError(f"No mock data for component: {component_name}")
        return json_data_map.get(component_name, {})

    with patch(patch_target) as mock_func:
        mock_func.side_effect = side_effect_func
        yield mock_func


@pytest.fixture(scope="function")
def mock_prometheus_usage_share(request):
    """
    Mock Prometheus response for calculating usage shares.
    """
    patch_target = "src.jupyterhub_cost_monitoring.query_cost_aws.query_usage"
    filename = "tests/data/test_data_usage.json"
    try:
        with open(f"{filename}") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Test data file not found: {filename}")

    usage_shares = _calculate_daily_cost_factors(data)

    with patch(patch_target) as mock_func:
        mock_func.return_value = usage_shares
        yield mock_func


@pytest.fixture(scope="function")
def mock_prometheus_user_group_info(request):
    """
    Mock Prometheus response for getting user group info.
    """
    targets = [
        "src.jupyterhub_cost_monitoring.query_usage.query_user_groups",
        "src.jupyterhub_cost_monitoring.query_cost_aws.query_user_groups",
    ]
    patches = [patch(t) for t in targets]
    mocks = [p.start() for p in patches]
    for m in mocks:
        with open("tests/data/test_output_user_group_info.json") as f:
            m.return_value = json.load(f)
    yield mocks
    for p in patches:
        p.stop()


@pytest.fixture(scope="function")
def mock_ce():
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
    aws_ce_client = boto3.client("ce")
    stubber = Stubber(aws_ce_client)
    for c in ["all", "home_storage", "core"]:
        with open(f"tests/data/test_data_cost_component_{c}.json") as f:
            response = json.load(f)
        stubber.add_response("get_cost_and_usage", response)
    with (
        stubber,
        patch(
            "src.jupyterhub_cost_monitoring.query_cost_aws.aws_ce_client", aws_ce_client
        ),
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
