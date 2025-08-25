"""
Query the Prometheus server to get usage of JupyterHub resources.
"""

import os
from collections import defaultdict
from datetime import datetime, timezone

import escapism
import requests
from yarl import URL

from .const_usage import USAGE_MAP

prometheus_host = os.environ.get(
    "SUPPORT_PROMETHEUS_SERVER_SERVICE_HOST", "http://localhost"
)
prometheus_port = int(os.environ.get("SUPPORT_PROMETHEUS_SERVER_SERVICE_PORT", 8080))


def query_prometheus(
    query: str, from_date: str, to_date: str, step: str
) -> requests.Response:
    """
    Query the Prometheus server with the given query.
    """
    prometheus_api = URL.build(
        scheme="http", host=prometheus_host, port=prometheus_port
    )
    parameters = {
        "query": query,
        "start": from_date,
        "end": to_date,
        "step": step,
    }
    query_api = URL(prometheus_api.with_path("/api/v1/query_range"))
    response = requests.get(query_api, params=parameters)
    response.raise_for_status()
    result = response.json()
    return result


def query_usage(
    from_date: str,
    to_date: str,
    hub_name: str | None,
    component_name: str | None,
    user_name: str | None,
) -> list[dict]:
    """
    Query usage cost factors per user from the Prometheus server.

    Returns daily usage cost factors (0-1) for each user, where cost factors represent
    each user's share of total resource usage and sum to 1 across all users
    within each date/hub/component combination.

    Args:
        from_date: Start date in string ISO format (YYYY-MM-DD).
        to_date: End date in string ISO format (YYYY-MM-DD).
        hub_name: Optional name of the hub to filter results.
        component_name: Optional name of the component to filter results.
        user_name: Optional name of the user to filter results.
    """
    result = []
    if component_name is None:
        for component, params in USAGE_MAP.items():
            response = query_prometheus(
                params["query"], from_date, to_date, step=params["step"]
            )
            result.extend(_process_response(response, component))
    else:
        response = query_prometheus(
            USAGE_MAP[component_name]["query"],
            from_date,
            to_date,
            step=USAGE_MAP[component_name]["step"],
        )
        result.extend(_process_response(response, component_name))
    # Calculate daily cost factors from absolute usage totals)
    result = _calculate_daily_cost_factors(result, hub_name=hub_name)
    # sort the result by date
    result.sort(key=lambda x: (x["date"], x["component"], x["hub"], x["user"]))
    result = _filter_json(result, hub=hub_name, user=user_name)
    return result


def _process_response(
    response: requests.Response,
    component_name: str,
) -> dict:
    """
    Process the response from the Prometheus server to extract absolute usage data.

    Converts the time series data into a list of usage records, then pivots by date
    and sums the absolute usage values across time steps within each date.

    If the component_name is home storage, then rename the escaped username used for the directory to the unescaped version.
    """
    result = []
    for data in response["data"]["result"]:
        hub = data["metric"]["namespace"]
        user = data["metric"]["username"]
        date = [
            datetime.fromtimestamp(value[0], tz=timezone.utc).strftime("%Y-%m-%d")
            for value in data["values"]
        ]
        usage = [float(value[1]) for value in data["values"]]
        result.append(
            {
                "hub": hub,
                "component": component_name,
                "user": user,
                "date": date,
                "value": usage,
            }
        )
    pivoted_result = _pivot_response_dict(result)
    processed_result = _sum_absolute_usage_by_date(pivoted_result)

    if component_name == "home storage":
        for entry in processed_result:
            if "shared" not in entry["user"]:
                entry["user"] = escapism.unescape(entry["user"], escape_char="-")
    return processed_result


def _filter_json(result: list[dict], **filters):
    return [
        item
        for item in result
        if all(filters[k] is None or item.get(k) == filters[k] for k in filters)
    ]


def _pivot_response_dict(result: list[dict]) -> list[dict]:
    """
    Pivot the response dictionary to have top-level keys as dates.
    """
    pivot = []
    for entry in result:
        for date, value in zip(entry["date"], entry["value"]):
            pivot.append(
                {
                    "date": date,
                    "user": entry["user"],
                    "hub": entry["hub"],
                    "component": entry["component"],
                    "value": value,
                }
            )
    return pivot


def _sum_absolute_usage_by_date(result: list[dict]) -> list[dict]:
    """
    Sum the absolute usage values by date.

    The Prometheus queries can return multiple absolute usage values per day.
    We sum across all entries within each date to get the total daily usage for each user.
    """
    sums = defaultdict(float)

    for entry in result:
        key = (
            entry["date"],
            entry["user"],
            entry["hub"],
            entry["component"],
        )
        sums[key] += entry["value"]

    return [
        {
            "date": date,
            "user": user,
            "hub": hub,
            "component": component,
            "value": total,
        }
        for (date, user, hub, component), total in sums.items()
    ]


def _calculate_daily_cost_factors(
    result: list[dict], hub_name: str | None = None
) -> list[dict]:
    """
    Calculate daily usage cost factors from absolute usage values.

    Converts absolute usage values to cost factors by dividing each user's usage
    by the total usage for all users within the appropriate grouping.

    If hub_name is None: cost factors are calculated across all hubs for each date/component
    If hub_name is specified: cost factors are calculated per hub for each date/component

    This ensures that cost factors sum to 1 for the appropriate grouping.
    """
    # Calculate total usage for the appropriate grouping
    totals = defaultdict(float)
    for entry in result:
        if hub_name is None:
            # When no specific hub requested, calculate totals across all hubs
            key = (entry["date"], entry["component"])
        else:
            # When specific hub requested, calculate totals per hub
            key = (entry["date"], entry["hub"], entry["component"])
        totals[key] += entry["value"]

    # Convert absolute values to cost factors
    for entry in result:
        if hub_name is None:
            # When no specific hub requested, use cross-hub totals
            key = (entry["date"], entry["component"])
        else:
            # When specific hub requested, use per-hub totals
            key = (entry["date"], entry["hub"], entry["component"])

        total = totals[key]
        if total > 0:
            entry["value"] = entry["value"] / total
        else:
            entry["value"] = 0.0
    return result
