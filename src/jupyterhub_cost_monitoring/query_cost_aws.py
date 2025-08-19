"""
Queries to AWS Cost Explorer to get different kinds of cost data.
"""

import functools
from datetime import datetime
from pprint import pformat

import boto3

from .cache import ttl_lru_cache
from .const_cost_aws import (
    FILTER_ATTRIBUTABLE_COSTS,
    FILTER_HOME_STORAGE_COSTS,
    FILTER_USAGE_COSTS,
    GRANULARITY_DAILY,
    GROUP_BY_HUB_TAG,
    GROUP_BY_SERVICE_DIMENSION,
    METRICS_UNBLENDED_COST,
    SERVICE_COMPONENT_MAP,
)
from .logs import get_logger
from .prometheus_client import query_user_usage_share

logger = get_logger(__name__)
aws_ce_client = boto3.client("ce")


@functools.cache
def _get_component_name(service_name):
    if service_name in SERVICE_COMPONENT_MAP:
        return SERVICE_COMPONENT_MAP[service_name]
    else:
        # only printed once per service name thanks to memoization
        logger.warning(f"Service '{service_name}' not categorized as a component yet")
        return "other"


def query_aws_cost_explorer(metrics, granularity, from_date, to_date, filter, group_by):
    """
    Function meant to be responsible for making the API call and handling
    pagination etc. Currently pagination isn't handled.
    """
    # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce/client/get_cost_and_usage.html#get-cost-and-usage
    response = aws_ce_client.get_cost_and_usage(
        Metrics=metrics,
        Granularity=granularity,
        TimePeriod={"Start": from_date, "End": to_date},
        Filter=filter,
        GroupBy=group_by,
    )
    # FIXME: Handle pagination, but until this is a need, error loudly instead
    #        of accounting partial costs only.
    if response.get("NextPageToken"):
        raise ValueError(
            f"A query with from '{from_date}' and to '{to_date}' led to "
            "jupyterhub-cost-monitoring needing to handle a paginated response "
            "and that hasn't been worked yet, it needs to be fixed."
        )

    return response


@ttl_lru_cache(seconds_to_live=3600)
def query_hub_names(from_date, to_date):
    # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce/client/get_tags.html
    response = aws_ce_client.get_tags(
        TimePeriod={"Start": from_date, "End": to_date},
        TagKey="2i2c:hub-name",
    )
    # response looks like...
    #
    # {
    #     "Tags": ["", "prod", "staging", "workshop"],
    #     "ReturnSize": 4,
    #     "TotalSize": 4,
    #     "ResponseMetadata": {
    #         "RequestId": "23736d32-9929-4b6a-8c4f-d80b1487ed37",
    #         "HTTPStatusCode": 200,
    #         "HTTPHeaders": {
    #             "date": "Fri, 20 Sep 2024 12:42:13 GMT",
    #             "content-type": "application/x-amz-json-1.1",
    #             "content-length": "70",
    #             "connection": "keep-alive",
    #             "x-amzn-requestid": "23736d32-9929-4b6a-8c4f-d80b1487ed37",
    #             "cache-control": "no-cache",
    #         },
    #         "RetryAttempts": 0,
    #     },
    # }
    #
    # The empty string is replaced with "shared"
    #
    hub_names = [t or "shared" for t in response["Tags"]]
    return hub_names


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs(from_date, to_date):
    """
    A query with processing of the response tailored to report both the total
    AWS account cost, and the total attributable cost.

    Not all costs will be successfully attributed, such as the cost of accessing
    the AWS Cost Explorer API - its not something that can be attributed based
    on a tag.
    """
    total_account_costs = _query_total_costs(
        from_date, to_date, add_attributable_costs_filter=False
    )
    total_attributable_costs = _query_total_costs(
        from_date, to_date, add_attributable_costs_filter=True
    )

    processed_response = total_account_costs + total_attributable_costs

    # the infinity plugin appears needs us to sort by date, otherwise it fails
    # to distinguish time series by the name field for some reason
    processed_response = sorted(processed_response, key=lambda x: x["date"])

    return processed_response


@ttl_lru_cache(seconds_to_live=3600)
def _query_total_costs(from_date, to_date, add_attributable_costs_filter):
    """
    A query with processing of the response tailored to report total costs.

    It can either be the total account costs, or only the attributable costs.
    """
    if add_attributable_costs_filter:
        name = "attributable"
        filter = {
            "And": [
                FILTER_USAGE_COSTS,
                FILTER_ATTRIBUTABLE_COSTS,
            ]
        }
    else:
        name = "account"
        filter = FILTER_USAGE_COSTS

    response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=filter,
        group_by=[],
    )

    # response["ResultsByTime"] is a list with entries looking like this...
    #
    # [
    #     {
    #         "Estimated": false,
    #         "Groups": [],
    #         "TimePeriod": {
    #             "End": "2024-07-28",
    #             "Start": "2024-07-27",
    #         },
    #         "Total": {
    #             "UnblendedCost": {
    #                 "Amount": "23.3110299724",
    #                 "Unit": "USD",
    #             },
    #         },
    #     },
    #     # ...
    # ]
    #
    # processed_response is a list with entries looking like this...
    #
    # [
    #     {
    #         "date":"2024-08-30",
    #         "cost":"12.19",
    #     },
    # ]
    #
    processed_response = [
        {
            "date": e["TimePeriod"]["Start"],
            "cost": f"{float(e['Total']['UnblendedCost']['Amount']):.2f}",
            "name": name,
        }
        for e in response["ResultsByTime"]
    ]
    return processed_response


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs_per_hub(from_date, to_date):
    """
    A query with processing of the response tailored to report total costs per
    hub, where costs not attributed to a specific hub is listed under 'shared'.
    """
    response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter={
            "And": [
                FILTER_USAGE_COSTS,
                FILTER_ATTRIBUTABLE_COSTS,
            ]
        },
        group_by=[
            GROUP_BY_HUB_TAG,
        ],
    )

    # response["ResultsByTime"] is a list with entries looking like this...
    #
    # [
    #     {
    #         "TimePeriod": {"Start": "2024-08-30", "End": "2024-08-31"},
    #         "Total": {},
    #         "Groups": [
    #             {
    #                 "Keys": ["2i2c:hub-name$"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "12.1930361882", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["2i2c:hub-name$prod"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "18.662514854", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["2i2c:hub-name$staging"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "0.000760628", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["2i2c:hub-name$workshop"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "0.1969903219", "Unit": "USD"}
    #                 },
    #             },
    #         ],
    #         "Estimated": False,
    #     },
    # ]
    #
    # processed_response is a list with entries looking like this...
    #
    # [
    #     {
    #         "date":"2024-08-30",
    #         "cost":"12.19",
    #         "name":"shared",
    #     },
    # ]
    #
    processed_response = []
    for e in response["ResultsByTime"]:
        processed_response.extend(
            [
                {
                    "date": e["TimePeriod"]["Start"],
                    "cost": f"{float(g['Metrics']['UnblendedCost']['Amount']):.2f}",
                    "name": g["Keys"][0].split("$", maxsplit=1)[1] or "shared",
                }
                for g in e["Groups"]
            ]
        )

    return processed_response


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs_per_component(from_date, to_date, hub_name=None, component=None):
    """
    A query with processing of the response tailored to report total costs per
    component - a grouping of services.

    If a hub_name is specified, component costs are filtered to only consider
    costs directly attributable to the hub name.

    If a component is specified, the response is filtered to only include that
    component only.
    """
    filter = {
        "And": [
            FILTER_USAGE_COSTS,
            FILTER_ATTRIBUTABLE_COSTS,
        ]
    }
    if hub_name == "shared":
        filter["And"].append(
            {
                "Tags": {
                    "Key": "2i2c:hub-name",
                    "MatchOptions": ["ABSENT"],
                },
            }
        )
    elif hub_name:
        filter["And"].append(
            {
                "Tags": {
                    "Key": "2i2c:hub-name",
                    "Values": [hub_name],
                    "MatchOptions": ["EQUALS"],
                },
            }
        )

    response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=filter,
        group_by=[GROUP_BY_SERVICE_DIMENSION],
    )

    # response["ResultsByTime"] is a list with entries looking like this...
    #
    # [
    #     {
    #         "TimePeriod": {"Start": "2024-08-30", "End": "2024-08-31"},
    #         "Total": {},
    #         "Groups": [
    #             {
    #                 "Keys": ["AWS Backup"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "2.4763369432", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["EC2 - Other"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "3.2334814259", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["Amazon Elastic Compute Cloud - Compute"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "12.5273401469", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["Amazon Elastic Container Service for Kubernetes"],
    #                 "Metrics": {"UnblendedCost": {"Amount": "2.4", "Unit": "USD"}},
    #             },
    #             {
    #                 "Keys": ["Amazon Elastic File System"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "9.4433542756", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["Amazon Elastic Load Balancing"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "0.6147035689", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["Amazon Simple Storage Service"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "0.1094078516", "Unit": "USD"}
    #                 },
    #             },
    #             {
    #                 "Keys": ["Amazon Virtual Private Cloud"],
    #                 "Metrics": {
    #                     "UnblendedCost": {"Amount": "0.24867778", "Unit": "USD"}
    #                 },
    #             },
    #         ],
    #         "Estimated": False,
    #     },
    # ]
    #

    # EC2 - Other is a service that can include costs for EBS volumes and snapshots
    # By default, these costs are mapped to the compute component, but
    # a part of the costs from EBS volumes and snapshots can be attributed to "home storage" too
    # so we need to query those costs separately and adjust the compute costs

    filter["And"].append(FILTER_HOME_STORAGE_COSTS)

    home_storage_ebs_cost_response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=filter,
        group_by=[GROUP_BY_SERVICE_DIMENSION],
    )

    logger.debug(pformat(home_storage_ebs_cost_response))

    # processed_response is a list with entries looking like this...
    #
    # [
    #     {
    #         "date": "2024-08-30",
    #         "cost": "12.19",
    #         "name": "home storage",
    #     },
    # ]
    #
    processed_response = []
    for e in response["ResultsByTime"]:
        # coalesce service costs to component costs
        component_costs = {}
        for g in e["Groups"]:
            service_name = g["Keys"][0]
            if not component:
                component = _get_component_name(service_name)
            cost = float(g["Metrics"]["UnblendedCost"]["Amount"])
            component_costs[component] = component_costs.get(component, 0.0) + cost

        processed_response.extend(
            [
                {
                    "date": e["TimePeriod"]["Start"],
                    "cost": f"{cost:.2f}",
                    "component": component,
                }
                for component, cost in component_costs.items()
            ]
        )

    # Create index for faster lookups by date and component name
    entries_by_date = {}
    for entry in processed_response:
        date = entry["date"]
        if date not in entries_by_date:
            entries_by_date[date] = {}
        entries_by_date[date][entry["name"]] = entry

    # Process home storage costs and adjust compute costs accordingly
    for home_e in home_storage_ebs_cost_response["ResultsByTime"]:
        date = home_e["TimePeriod"]["Start"]

        # Calculate total home storage cost for this date
        home_storage_cost = 0.0
        for g in home_e["Groups"]:
            if g["Keys"][0] == "EC2 - Other":
                home_storage_cost += float(g["Metrics"]["UnblendedCost"]["Amount"])

        if home_storage_cost > 0:
            date_entries = entries_by_date.get(date, {})

            # Subtract from compute component (EC2 - Other maps to compute)
            compute_entry = date_entries.get("compute")
            if compute_entry:
                current_compute_cost = float(compute_entry["cost"])
                new_compute_cost = max(0.0, current_compute_cost - home_storage_cost)
                compute_entry["cost"] = f"{new_compute_cost:.2f}"
                logger.debug(
                    f"Adjusted compute cost for {date}: {current_compute_cost:.2f} -> {new_compute_cost:.2f}"
                )

            # Add to home storage component
            home_storage_entry = date_entries.get("home storage")
            if home_storage_entry:
                current_home_storage_cost = float(home_storage_entry["cost"])
                new_home_storage_cost = current_home_storage_cost + home_storage_cost
                home_storage_entry["cost"] = f"{new_home_storage_cost:.2f}"
                logger.debug(
                    f"Updated home storage cost for {date}: {current_home_storage_cost:.2f} -> {new_home_storage_cost:.2f}"
                )
            else:
                # Create new home storage entry if it doesn't exist
                new_entry = {
                    "date": date,
                    "cost": f"{home_storage_cost:.2f}",
                    "name": "home storage",
                }
                # Update index
                if date not in entries_by_date:
                    entries_by_date[date] = {}
                entries_by_date[date]["home storage"] = new_entry
                logger.debug(
                    f"Added new home storage entry for {date}: {home_storage_cost:.2f}"
                )

    # Generate final response from index, sorted by date
    final_response = []
    for date in sorted(entries_by_date.keys()):
        for _, entry in entries_by_date[date].items():
            final_response.append(entry)

    return final_response


def query_total_storage_costs_per_user(from_date, to_date, hub: str = None):
    """
    Query total storage costs per user by combining AWS storage costs with Prometheus usage data.

    Args:
        from_date: Start date for the query (YYYY-MM-DD format)
        to_date: End date for the query (YYYY-MM-DD format)
        hub: The hub namespace to query (optional, if None queries all hubs)

    Returns:
        Dict mapping date to dict of user (username) to their storage cost
    """
    # Get home storage costs from AWS for this hub
    home_storage_costs = query_total_costs_per_component(from_date, to_date, hub)

    # Filter to only home storage costs
    storage_costs_by_date = {}
    for entry in home_storage_costs:
        if entry["name"] == "home storage":
            storage_costs_by_date[entry["date"]] = float(entry["cost"])

    # Convert dates to Unix timestamps for Prometheus query
    start_dt = datetime.strptime(from_date, "%Y-%m-%d")
    end_dt = datetime.strptime(to_date, "%Y-%m-%d")
    prometheus_from = str(int(start_dt.timestamp()))
    prometheus_to = str(int(end_dt.timestamp()))

    # Get user usage percentages from Prometheus
    usage_shares = query_user_usage_share(prometheus_from, prometheus_to, hub)

    # Calculate per-user costs by weighting total cost with usage percentages
    result = {}
    for date, users in usage_shares.items():
        total_storage_cost = storage_costs_by_date.get(date, 0.0)
        result[date] = {}

        for user, usage_share in users.items():
            user_cost = total_storage_cost * usage_share
            result[date][user] = round(user_cost, 4)

    return result
