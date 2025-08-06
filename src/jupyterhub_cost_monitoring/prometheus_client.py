import os
from datetime import datetime
from typing import Dict

import requests

PROMETHEUS_HOST = os.environ.get("PROMETHEUS_HOST", "http://localhost:9090")


def query_user_usage_share(
    from_date: str, to_date: str, hub: str = None
) -> Dict[str, Dict[str, float]]:
    """
    Query Prometheus for the share of per-user disk usage over time.

    Args:
        from_date: Start date for the query (RFC3339 format or Unix timestamp)
        to_date: End date for the query (RFC3339 format or Unix timestamp)
        hub: The hub namespace to query (optional, if None queries all namespaces)

    Returns:
        Dict mapping date to dict of directory (username) to their usage percentage
    """
    if hub:
        namespace_filter = f'namespace=~"{hub}"'
    else:
        namespace_filter = ""

    query = f"""
    sum(dirsize_total_size_bytes{{{namespace_filter}}}) by (directory)
    /
    ignoring (directory) group_left sum(dirsize_total_size_bytes{{{namespace_filter}}})
    """

    params = {
        "query": query.strip(),
        "start": from_date,
        "end": to_date,
        "step": "1d",  # Daily resolution
    }

    response = requests.get(f"{PROMETHEUS_HOST}/api/v1/query_range", params=params)
    response.raise_for_status()

    data = response.json()
    result = {}

    if data.get("status") == "success" and data.get("data", {}).get("result"):
        for item in data["data"]["result"]:
            directory = item["metric"].get("directory", "")
            values = item.get("values", [])

            for timestamp, value in values:
                # Convert timestamp to date string
                date = datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d")

                if date not in result:
                    result[date] = {}

                result[date][directory] = float(value)

    # Sort each day's results by usage share in descending order
    for date in result:
        result[date] = dict(
            sorted(result[date].items(), key=lambda item: item[1], reverse=True)
        )

    # TODO: Should we divide the shared directories' usage among the users?
    # Or, treat it like a separate user?

    return result


# if __name__ == "__main__":
#     # Example usage for last 7 days
#     from datetime import datetime, timedelta

#     hub_name = None
#     # or define a specific hub
#     hub_name = "staging"
#     end_date = datetime.now()
#     start_date = end_date - timedelta(days=7)

#     # Format dates for Prometheus (Unix timestamps)
#     from_date = str(int(start_date.timestamp()))
#     to_date = str(int(end_date.timestamp()))

#     usage_share = query_user_usage_share(from_date, to_date, hub_name)

#     print(f"User disk usage share for {hub_name} (last 7 days):")
#     for date in sorted(usage_share.keys()):
#         print(f"\nDate: {date}")
#         total_usage = sum(usage_share[date].values())
#         print(f"  Total usage share: {total_usage:.6f}")
#         for user, share in usage_share[date].items():
#             print(f"  {user}: {share*100:.2f}%")
