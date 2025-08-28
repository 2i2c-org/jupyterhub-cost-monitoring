import json
from datetime import datetime, timezone

import pytest


@pytest.fixture(scope="function")
def input_data_usage():
    with open("tests/test_data_usage.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def input_data_cost():
    with open("tests/test_data_cost.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_hub():
    with open("tests/test_output_hub.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_component():
    with open("tests/test_output_component.json") as f:
        data = json.load(f)
    return data


# Date-specific fixtures for date_utils tests


@pytest.fixture
def sample_utc_datetime():
    """Sample UTC datetime for testing."""
    return datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)


@pytest.fixture
def sample_date_range():
    """Sample DateRange for testing."""
    from src.jupyterhub_cost_monitoring.date_utils import DateRange

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 31, tzinfo=timezone.utc)
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
