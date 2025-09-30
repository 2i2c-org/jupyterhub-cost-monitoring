"""
Comprehensive tests for date handling utilities.

Tests cover UTC conversion, DateRange functionality, date parsing,
API-specific formatting, and caching integration.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.jupyterhub_cost_monitoring.cache import ttl_lru_cache
from src.jupyterhub_cost_monitoring.date_utils import (
    DateRange,
    ensure_utc_datetime,
    parse_from_to_in_query_params,
)


class TestEnsureUTCDateTime:
    """Test ensure_utc_datetime function for proper UTC conversion."""

    def test_timezone_naive_string_assumes_utc(self):
        """Test that timezone-naive strings are assumed to be UTC."""
        result = ensure_utc_datetime("2025-01-15")
        expected = datetime(2025, 1, 15, tzinfo=timezone.utc)
        assert result == expected
        assert result.tzinfo == timezone.utc

    def test_timezone_aware_string_converts_to_utc(self):
        """Test that timezone-aware strings are converted to UTC."""
        # Test with EST (UTC-5)
        result = ensure_utc_datetime("2025-01-15T10:00:00-05:00")
        expected = datetime(
            2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc
        )  # 10 AM EST = 3 PM UTC
        assert result == expected
        assert result.tzinfo == timezone.utc

    def test_iso_formats(self):
        """Test various ISO format inputs."""
        test_cases = [
            ("2025-01-15", datetime(2025, 1, 15, tzinfo=timezone.utc)),
            ("2025-01-15T00:00:00", datetime(2025, 1, 15, tzinfo=timezone.utc)),
            (
                "2025-01-15T12:30:45",
                datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc),
            ),
            # Z suffix indicates UTC timezone (Zulu time)
            (
                "2025-01-15T12:30:45Z",
                datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc),
            ),
        ]

        for input_str, expected in test_cases:
            result = ensure_utc_datetime(input_str)
            assert result == expected
            assert result.tzinfo == timezone.utc

    def test_utc_string_unchanged(self):
        """Test that UTC strings remain unchanged."""
        result = ensure_utc_datetime("2025-01-15T12:00:00+00:00")
        expected = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_different_timezones(self):
        """Test conversion from various timezones to UTC."""
        test_cases = [
            # PST (UTC-8) to UTC
            (
                "2025-01-15T08:00:00-08:00",
                datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
            ),
            # JST (UTC+9) to UTC
            (
                "2025-01-15T18:00:00+09:00",
                datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
            ),
            # CET (UTC+1) to UTC
            (
                "2025-01-15T13:00:00+01:00",
                datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for input_str, expected in test_cases:
            result = ensure_utc_datetime(input_str)
            assert result == expected


class TestDateRange:
    """Test DateRange class functionality."""

    def test_daterange_creation(self):
        """Test basic DateRange object creation."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        dr = DateRange(start_date=start, end_date=end)

        assert dr.start_date == start
        assert dr.end_date == end

    def test_daterange_immutability(self):
        """Test that DateRange is immutable (frozen dataclass)."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        dr = DateRange(start_date=start, end_date=end)

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            dr.start_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        with pytest.raises(AttributeError):
            dr.end_date = datetime(2025, 2, 28, tzinfo=timezone.utc)

    def test_daterange_hashability(self):
        """Test that DateRange objects are hashable and can be used as dict keys."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        dr1 = DateRange(start_date=start, end_date=end)
        dr2 = DateRange(start_date=start, end_date=end)

        # Test hashable
        assert hash(dr1) == hash(dr2)

        # Test usable as dict key
        test_dict = {dr1: "test_value"}
        assert test_dict[dr2] == "test_value"

    def test_daterange_equality(self):
        """Test DateRange equality comparison."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        dr1 = DateRange(start_date=start, end_date=end)
        dr2 = DateRange(start_date=start, end_date=end)
        dr3 = DateRange(
            start_date=start, end_date=datetime(2025, 2, 1, tzinfo=timezone.utc)
        )

        assert dr1 == dr2
        assert dr1 != dr3

    def test_aws_range_formatting(self):
        """Test AWS date range formatting (exclusive end date, YYYY-MM-DD format)."""
        start = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, 8, 15, 30, tzinfo=timezone.utc)
        dr = DateRange(start_date=start, end_date=end)

        aws_from, aws_to = dr.aws_range

        # Should be YYYY-MM-DD format
        assert aws_from == "2025-01-15"
        # End date should be +1 day for AWS exclusive range
        assert aws_to == "2025-02-01"

    def test_prometheus_range_formatting(self):
        """Test Prometheus date range formatting (inclusive dates, ISO format)."""
        start = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, 8, 15, 30, tzinfo=timezone.utc)
        dr = DateRange(start_date=start, end_date=end)

        prom_from, prom_to = dr.prometheus_range

        # Should be full ISO format with normalized times, no +1 day adjustment
        assert prom_from == "2025-01-15T00:00:00+00:00"  # Normalized to start of day
        assert prom_to == "2025-01-31T23:59:59.999999+00:00"  # Normalized to end of day

    def test_same_logical_range_different_formats(self):
        """Test that AWS and Prometheus formats represent the same logical date range."""
        # Create range for January 1-31, 2025
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        dr = DateRange(start_date=start, end_date=end)

        aws_from, aws_to = dr.aws_range
        prom_from, prom_to = dr.prometheus_range

        # AWS: exclusive range should be "2025-01-01" to "2025-02-01"
        assert aws_from == "2025-01-01"
        assert aws_to == "2025-02-01"  # +1 day for exclusive end

        # Prometheus: inclusive range should preserve normalized timestamps
        assert prom_from == "2025-01-01T00:00:00+00:00"
        assert prom_to == "2025-01-31T23:59:59.999999+00:00"


class TestParseDateRangeParams:
    """Test parse_from_to_in_query_params function."""

    def test_default_date_range(self):
        """Test default 30-day range behavior."""
        with patch("src.jupyterhub_cost_monitoring.date_utils.datetime") as mock_dt:
            # Mock current time as 2025-02-15 midnight UTC
            mock_now = datetime(2025, 2, 15, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = parse_from_to_in_query_params()

            # Should default to 30 days before current date
            expected_start = mock_now - timedelta(days=30)
            expected_end = mock_now

            assert result.start_date == expected_start
            assert result.end_date == expected_end

    def test_timezone_handling_in_parsing(self):
        """Test that timezone-aware input dates are properly converted to UTC."""
        # Input with timezone
        result = parse_from_to_in_query_params(
            "2025-01-01T10:00:00-05:00",
            "2025-01-31T15:00:00+02:00",  # EST  # CET
        )

        # Should be converted to UTC
        expected_start = datetime(
            2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc
        )  # 10 AM EST = 3 PM UTC
        expected_end = datetime(
            2025, 1, 31, 13, 0, 0, tzinfo=timezone.utc
        )  # 3 PM CET = 1 PM UTC

        assert result.start_date == expected_start
        assert result.end_date == expected_end


class TestCacheIntegration:
    """Test DateRange compatibility with ttl_lru_cache."""

    def test_daterange_as_cache_key(self):
        """Test that DateRange objects work as cache keys."""

        call_count = 0

        @ttl_lru_cache(seconds_to_live=300)
        def cached_function(date_range: DateRange) -> str:
            nonlocal call_count
            call_count += 1
            return f"Result for {date_range.start_date.date()}"

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        dr1 = DateRange(start_date=start, end_date=end)
        dr2 = DateRange(start_date=start, end_date=end)  # Identical range

        # First call
        result1 = cached_function(dr1)
        # Second call with identical DateRange should hit cache
        result2 = cached_function(dr2)

        assert result1 == result2
        assert result1 == "Result for 2025-01-01"
        assert call_count == 1  # Function should be called only once

    def test_cache_miss_with_different_ranges(self):
        """Test that different DateRange objects result in cache misses."""
        call_count = 0

        @ttl_lru_cache(seconds_to_live=300)
        def cached_function(date_range: DateRange) -> str:
            nonlocal call_count
            call_count += 1
            return f"Call #{call_count} for {date_range.start_date.date()}"

        start1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end1 = datetime(2025, 1, 31, tzinfo=timezone.utc)
        january_range = DateRange(start_date=start1, end_date=end1)

        start2 = datetime(2025, 2, 1, tzinfo=timezone.utc)
        end2 = datetime(2025, 2, 28, tzinfo=timezone.utc)
        february_range = DateRange(start_date=start2, end_date=end2)

        result1 = cached_function(january_range)
        result2 = cached_function(february_range)

        # Should be different results (cache miss)
        assert result1 != result2
        assert call_count == 2  # Function called twice

    def test_cache_hit_with_same_dates_different_times(self):
        """Test that DateRange objects with same dates but different times result in cache hits."""
        call_count = 0

        @ttl_lru_cache(seconds_to_live=300)
        def cached_function(date_range: DateRange) -> str:
            nonlocal call_count
            call_count += 1
            return f"Call #{call_count} for {date_range.start_date.date()}"

        # Same dates but different times
        start1 = datetime(2025, 1, 1, 8, 30, 15, tzinfo=timezone.utc)
        end1 = datetime(2025, 1, 31, 14, 45, 22, tzinfo=timezone.utc)
        morning_range = DateRange(start_date=start1, end_date=end1)

        start2 = datetime(2025, 1, 1, 16, 20, 55, tzinfo=timezone.utc)
        end2 = datetime(2025, 1, 31, 9, 12, 8, tzinfo=timezone.utc)
        evening_range = DateRange(start_date=start2, end_date=end2)

        result1 = cached_function(morning_range)
        result2 = cached_function(evening_range)

        # Should be same results (cache hit) because dates are the same
        assert result1 == result2
        assert call_count == 1  # Function should be called only once

    def test_daterange_normalization(self):
        """Test that DateRange normalizes times for consistent caching."""
        # Test start date normalization to 00:00:00
        start_with_time = datetime(2025, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        end_with_time = datetime(2025, 1, 31, 8, 15, 30, tzinfo=timezone.utc)
        time_specific_range = DateRange(
            start_date=start_with_time, end_date=end_with_time
        )

        # Original dates should be preserved
        assert time_specific_range.start_date.hour == 15
        assert time_specific_range.end_date.hour == 8

        # Normalized start date should be normalized to midnight
        assert time_specific_range.normalized_start_date.hour == 0
        assert time_specific_range.normalized_start_date.minute == 0
        assert time_specific_range.normalized_start_date.second == 0
        assert time_specific_range.normalized_start_date.microsecond == 0

        # Normalized end date should be normalized to end of day
        assert time_specific_range.normalized_end_date.hour == 23
        assert time_specific_range.normalized_end_date.minute == 59
        assert time_specific_range.normalized_end_date.second == 59
        assert time_specific_range.normalized_end_date.microsecond == 999999

    def test_daterange_hash_consistency_across_times(self):
        """Test that DateRange objects with same dates but different times have same hash."""
        # Same dates, different times
        start1 = datetime(2025, 1, 1, 2, 30, tzinfo=timezone.utc)
        end1 = datetime(2025, 1, 31, 18, 45, tzinfo=timezone.utc)
        early_range = DateRange(start_date=start1, end_date=end1)

        start2 = datetime(2025, 1, 1, 22, 15, tzinfo=timezone.utc)
        end2 = datetime(2025, 1, 31, 6, 20, tzinfo=timezone.utc)
        late_range = DateRange(start_date=start2, end_date=end2)

        # Should have same hash despite different input times
        assert hash(early_range) == hash(late_range)

        # Should be usable as same dict key
        test_dict = {early_range: "value1"}
        test_dict[late_range] = "value2"
        assert len(test_dict) == 1  # Only one key because they hash the same
        assert test_dict[early_range] == "value2"  # Second assignment overwrote first
