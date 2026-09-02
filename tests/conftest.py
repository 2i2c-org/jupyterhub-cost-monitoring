import os
from datetime import datetime, timezone

import pytest

from jupyterhub_cost_monitoring.date_utils import DateRange

os.environ["CLUSTER_NAME"] = "test-cluster"


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


@pytest.fixture
def aws_date_range() -> DateRange:
    return DateRange(datetime(2026, 6, 20), datetime(2026, 6, 27))
