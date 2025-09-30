"""
Utility functions for date and timezone handling.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def ensure_utc_datetime(date_str: str) -> datetime:
    """
    Parse a date string and ensure it's timezone-aware in UTC.

    Args:
        date_str: Date string in ISO format (with or without timezone)

    Returns:
        Timezone-aware datetime object in UTC
    """
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        # Assume UTC if no timezone provided
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if timezone-aware
        dt = dt.astimezone(timezone.utc)
    return dt


@dataclass(frozen=True)
class DateRange:
    """
    Represents a date range with proper formatting for different APIs.

    This class stores the original start and end dates in UTC timezone and provides
    properties to format them correctly for different APIs that have different
    date range requirements:
    - AWS Cost Explorer: Uses exclusive end dates (end date not included in range)
    - Prometheus: Uses inclusive dates with ISO timestamp format

    This ensures consistent date ranges across different API calls while respecting
    each API's specific formatting requirements.

    Note: For caching purposes, hashing is based only on the normalized date components
    to ensure consistent caching regardless of input time precision.
    """

    start_date: datetime  # Original start date in UTC
    end_date: datetime  # Original end date in UTC

    @property
    def normalized_start_date(self) -> datetime:
        """Return start date normalized to midnight UTC for consistent caching."""
        return self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    @property
    def normalized_end_date(self) -> datetime:
        """Return end date normalized to end of day UTC for consistent caching."""
        return self.end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    def __hash__(self):
        """Hash based on normalized dates for consistent caching."""
        return hash((self.normalized_start_date, self.normalized_end_date))

    def __eq__(self, other):
        """Equality based on normalized dates for consistent caching."""
        if not isinstance(other, DateRange):
            return False
        return (
            self.normalized_start_date == other.normalized_start_date
            and self.normalized_end_date == other.normalized_end_date
        )

    @property
    def aws_range(self) -> tuple[str, str]:
        """
        Format dates for AWS Cost Explorer API.

        AWS Cost Explorer uses exclusive end dates, meaning the end date is not
        included in the query results. To include the intended end date, we add
        one day to it. Returns dates in YYYY-MM-DD string format as required by AWS API.

        Returns:
            Tuple of (start_date_str, end_date_str) formatted for AWS Cost Explorer
        """
        return (
            self.normalized_start_date.strftime("%Y-%m-%d"),
            (self.normalized_end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    @property
    def prometheus_range(self) -> tuple[str, str]:
        """
        Format dates for Prometheus API.

        Prometheus uses inclusive date ranges with ISO format timestamps.
        Both start and end dates are included in the query results.

        Returns:
            Tuple of (start_date_iso, end_date_iso) formatted for Prometheus
        """
        return (
            self.normalized_start_date.isoformat(),
            self.normalized_end_date.isoformat(),
        )


def parse_from_to_in_query_params(
    from_date: str | None = None,
    to_date: str | None = None,
) -> DateRange:
    """
    Parse "from" and "to" query parameters into a DateRange object.

    This function handles the common pattern of parsing date query parameters
    from API requests. It accepts date strings in various ISO formats (YYYY-MM-DD
    or full ISO datetime strings with timezone info) and returns a DateRange object
    that can format dates appropriately for different APIs.

    Args:
        from_date: Start date string in ISO format (YYYY-MM-DD or full ISO datetime).
                  If None, defaults to 30 days prior to the end date.
        to_date: End date string in ISO format (YYYY-MM-DD or full ISO datetime).
                If None, defaults to current date (UTC midnight).

    Returns:
        DateRange object containing the parsed and validated date range in UTC.
        Use .aws_range or .prometheus_range properties to get API-specific formatting.

    Validation Rules:
    - End date cannot be in the future (clamped to current date)
    - Start date cannot be >= current date (adjusted to 1 day before end date)
    - Default range is 30 days ending today

    Note:
    Python 3.11+ is required to parse datetime strings like "2024-07-27T15:50:18.231Z"
    with a 'Z' suffix. Grafana's `${__from:date}` variable outputs UTC-based dates,
    but custom formatting may not preserve timezone info, so we handle both cases.
    """
    # Get current date at midnight UTC for consistent date boundaries
    now_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Parse and set defaults for date parameters
    if to_date:
        to_date = ensure_utc_datetime(to_date)
    else:
        to_date = now_date

    if from_date:
        from_date = ensure_utc_datetime(from_date)
    else:
        # Default to 30 days prior to end date
        from_date = to_date - timedelta(days=30)

    # Apply validation rules to prevent API errors

    # Prevent "end date past the beginning of next month" errors from AWS
    if to_date > now_date:
        to_date = now_date

    # Prevent "Start date (and hour) should be before end date (and hour)" errors
    if from_date >= now_date:
        from_date = to_date - timedelta(days=1)

    return DateRange(start_date=from_date, end_date=to_date)
