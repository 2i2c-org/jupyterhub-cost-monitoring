"""
Queries to AWS Cost Explorer to get different kinds of cost data.
"""

import copy
import functools
from pprint import pformat

import boto3

from .cache import ttl_lru_cache
from .const_cost_aws import (
    FILTER_ATTRIBUTABLE_COSTS,
    FILTER_CORE_COSTS,
    FILTER_HOME_STORAGE_COSTS,
    FILTER_USAGE_COSTS,
    GRANULARITY_DAILY,
    GROUP_BY_HUB_TAG,
    GROUP_BY_SERVICE_DIMENSION,
    METRICS_UNBLENDED_COST,
    SERVICE_COMPONENT_MAP,
)
from .date_utils import DateRange
from .logs import get_logger
from .query_usage import _filter_json, query_usage, query_user_groups

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
def query_hub_names(date_range: DateRange):
    """
    Query hub names from AWS Cost Explorer within the given date range.

    Args:
        date_range: DateRange object containing the time period for the query

    Returns:
        List of hub names, with empty/None values converted to "support"
    """
    # Use AWS-formatted dates (exclusive end date) for Cost Explorer API
    from_date, to_date = date_range.aws_range

    # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce/client/get_tags.html
    response = aws_ce_client.get_tags(
        TimePeriod={"Start": from_date, "End": to_date},
        TagKey="2i2c:hub-name",
    )
    hub_names = [t or "support" for t in response["Tags"]]
    return hub_names


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs(date_range: DateRange):
    """
    Query total costs from AWS Cost Explorer for the given date range.

    Reports both the total AWS account cost and the total attributable cost.
    Not all costs will be successfully attributed, such as the cost of accessing
    the AWS Cost Explorer API - its not something that can be attributed based
    on a tag.

    Args:
        date_range: DateRange object containing the time period for the query

    Returns:
        List of cost entries with 'date', 'cost', and 'name' fields, sorted by date
    """
    total_account_costs = _query_total_costs(
        date_range, add_attributable_costs_filter=False
    )
    total_attributable_costs = _query_total_costs(
        date_range, add_attributable_costs_filter=True
    )

    processed_response = total_account_costs + total_attributable_costs

    # the infinity plugin appears needs us to sort by date, otherwise it fails
    # to distinguish time series by the name field for some reason
    processed_response = sorted(processed_response, key=lambda x: x["date"])

    return processed_response


@ttl_lru_cache(seconds_to_live=3600)
def _query_total_costs(date_range: DateRange, add_attributable_costs_filter):
    """
    Internal function to query total costs from AWS Cost Explorer.

    Can query either the total account costs or only the attributable costs
    based on the add_attributable_costs_filter parameter.

    Args:
        date_range: DateRange object containing the time period for the query
        add_attributable_costs_filter: If True, only include attributable costs

    Returns:
        List of cost entries with 'date', 'cost', and 'name' fields
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

    # Use AWS-formatted dates (exclusive end date) for Cost Explorer API
    from_date, to_date = date_range.aws_range

    response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=filter,
        group_by=[],
    )

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
def query_total_costs_per_hub(date_range: DateRange):
    """
    Query total costs per hub from AWS Cost Explorer for the given date range.

    Costs not attributed to a specific hub are listed under 'support'.

    Args:
        date_range: DateRange object containing the time period for the query

    Returns:
        List of cost entries with 'date', 'cost', and 'name' (hub name) fields
    """
    # Use AWS-formatted dates (exclusive end date) for Cost Explorer API
    from_date, to_date = date_range.aws_range

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

    processed_response = []
    for e in response["ResultsByTime"]:
        processed_response.extend(
            [
                {
                    "date": e["TimePeriod"]["Start"],
                    "cost": f"{float(g['Metrics']['UnblendedCost']['Amount']):.2f}",
                    "name": g["Keys"][0].split("$", maxsplit=1)[1] or "support",
                }
                for g in e["Groups"]
            ]
        )

    return processed_response


def _process_home_storage_costs(entries_by_date, home_storage_ebs_cost_response):
    """
    Helper function to get home storage costs and deduct this from the compute component costs.
    This is because EBS volumes are included in the EC2 - Other service, which is mapped to the
    compute component by default.

    Args:
        entries_by_date: Dictionary indexed by date containing component entries
        home_storage_ebs_cost_response: AWS Cost Explorer response for home storage EBS costs
    """
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
                    "component": "home storage",
                }
                # Update index
                if date not in entries_by_date:
                    entries_by_date[date] = {}
                entries_by_date[date]["home storage"] = new_entry
                logger.debug(
                    f"Added new home storage entry for {date}: {home_storage_cost:.2f}"
                )


def _add_hub_filter(filter_dict: dict, hub_name: str = None) -> None:
    """
    Add hub-specific filtering to a given filter dictionary.

    Args:
        filter_dict: The filter dictionary to modify (must have "And" key)
        hub_name: The hub name to filter by. If "support", filters for absent hub tags.
                 If a specific name, filters for that hub. If None, no filter added.
    """
    if hub_name == "support":
        filter_dict["And"].append(
            {
                "Tags": {
                    "Key": "2i2c:hub-name",
                    "MatchOptions": ["ABSENT"],
                },
            }
        )
    elif hub_name:
        filter_dict["And"].append(
            {
                "Tags": {
                    "Key": "2i2c:hub-name",
                    "Values": [hub_name],
                    "MatchOptions": ["EQUALS"],
                },
            }
        )


def _create_base_filter() -> dict:
    """
    Create the base filter used for most cost queries.

    Returns:
        Base filter dictionary with usage and attributable cost filters
    """
    return {
        "And": [
            FILTER_USAGE_COSTS,
            FILTER_ATTRIBUTABLE_COSTS,
        ]
    }


def _process_core_costs(entries_by_date, core_cost_response):
    """
    Helper function to get core infrastructure costs and deduct this from compute costs.

    This is because core node compute and root volumes, support EBS volumes
    and NAT Gateway (if it exists), are mapped to compute by default under
    the EC2 - Other service.

    Args:
        entries_by_date: Dictionary indexed by date containing component entries
        core_cost_response: AWS Cost Explorer response for core costs
    """
    logger.debug(
        f"Processing core costs: {pformat(core_cost_response['ResultsByTime'])}"
    )
    for core_e in core_cost_response["ResultsByTime"]:
        date = core_e["TimePeriod"]["Start"]

        # Calculate total core cost for this date
        core_cost = 0.0
        for g in core_e["Groups"]:
            core_cost += float(g["Metrics"]["UnblendedCost"]["Amount"])

        if core_cost > 0:
            date_entries = entries_by_date.get(date, {})

            # Subtract from compute component (EC2 - Other maps to compute)
            compute_entry = date_entries.get("compute")
            if compute_entry:
                current_compute_cost = float(compute_entry["cost"])
                new_compute_cost = max(0.0, current_compute_cost - core_cost)
                compute_entry["cost"] = f"{new_compute_cost:.2f}"
                logger.debug(
                    f"Adjusted compute cost for {date} (core cost): {current_compute_cost:.2f} -> {new_compute_cost:.2f}"
                )

            # Add to core component
            core_entry = date_entries.get("core")
            if core_entry:
                current_core_cost = float(core_entry["cost"])
                new_core_cost = current_core_cost + core_cost
                core_entry["cost"] = f"{new_core_cost:.2f}"
                logger.debug(
                    f"Updated core cost for {date}: {current_core_cost:.2f} -> {new_core_cost:.2f}"
                )
            else:
                # Create new core entry if it doesn't exist
                new_entry = {
                    "date": date,
                    "cost": f"{core_cost:.2f}",
                    "component": "core",
                }
                # Update index
                if date not in entries_by_date:
                    entries_by_date[date] = {}
                entries_by_date[date]["core"] = new_entry
                logger.debug(f"Added new core entry for {date}: {core_cost:.2f}")


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs_per_component(
    date_range: DateRange,
    hub_name: str = None,
    component: str = None,
):
    """
    Query total costs per component from AWS Cost Explorer for the given date range.

    A component is a logical grouping of AWS services (e.g., compute, storage).

    Args:
        date_range: DateRange object containing the time period for the query
        hub_name: The hub name to filter by. If "support", filters for support costs not tied to any specific hub. If a specific name, filters for that hub. If None, queries all hubs.
        component: The component to filter by. If None, queries all components.

    Returns:
        List of dicts with keys: date, cost, component
    """
    # Create base filter and add hub-specific filtering
    base_filter = _create_base_filter()
    _add_hub_filter(base_filter, hub_name)

    # Use AWS-formatted dates (exclusive end date) for Cost Explorer API
    from_date, to_date = date_range.aws_range

    response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=base_filter,
        group_by=[GROUP_BY_SERVICE_DIMENSION],
    )

    processed_response = []

    logger.debug(f"Processing response: {pformat(response['ResultsByTime'])}")

    for e in response["ResultsByTime"]:
        # coalesce service costs to component costs
        component_costs = {}
        for g in e["Groups"]:
            service_name = g["Keys"][0]
            component_name = _get_component_name(service_name)
            cost = float(g["Metrics"]["UnblendedCost"]["Amount"])
            component_costs[component_name] = (
                component_costs.get(component_name, 0.0) + cost
            )

        # Filter to specific component if requested
        logger.debug(f"Component costs before filtering: {component_costs}")
        if component:
            component_costs = {
                k: v for k, v in component_costs.items() if k == component
            }

        processed_response.extend(
            [
                {
                    "date": e["TimePeriod"]["Start"],
                    "cost": f"{cost:.2f}",
                    "component": component_name,
                }
                for component_name, cost in component_costs.items()
            ]
        )

    # Create index for faster lookups by date and component name
    entries_by_date = {}
    for entry in processed_response:
        date = entry["date"]
        if date not in entries_by_date:
            entries_by_date[date] = {}
        entries_by_date[date][entry["component"]] = entry

    logger.debug(f"Entries by date before deduplication: {entries_by_date}\n\n")

    # EC2 - Other is a service that can include costs for EBS volumes and snapshots
    # By default, these costs are mapped to the compute component, but
    # a part of the costs from EBS volumes and snapshots can be attributed to "home storage" too
    # so we need to query those costs separately and adjust the compute costs

    # Create home storage filter using the same base filter and hub filtering
    home_storage_filter = _create_base_filter()
    _add_hub_filter(home_storage_filter, hub_name)
    home_storage_filter["And"].append(FILTER_HOME_STORAGE_COSTS)

    home_storage_ebs_cost_response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=home_storage_filter,
        group_by=[GROUP_BY_SERVICE_DIMENSION],
    )

    # Process home storage costs and adjust compute costs accordingly
    _process_home_storage_costs(entries_by_date, home_storage_ebs_cost_response)

    logger.debug(
        f"Entries by date after home storage processing: {entries_by_date}\n\n"
    )

    # Query core costs (core nodes, hub databases, support components)
    # These should be subtracted from compute and added to a "core" component
    core_cost_filter = _create_base_filter()
    _add_hub_filter(core_cost_filter, hub_name)
    core_cost_filter["And"].append(FILTER_CORE_COSTS)

    core_cost_response = query_aws_cost_explorer(
        metrics=[METRICS_UNBLENDED_COST],
        granularity=GRANULARITY_DAILY,
        from_date=from_date,
        to_date=to_date,
        filter=core_cost_filter,
        group_by=[GROUP_BY_SERVICE_DIMENSION],
    )

    # Process core costs and adjust compute costs accordingly
    _process_core_costs(entries_by_date, core_cost_response)

    logger.debug(f"Entries by date after core cost processing: {entries_by_date}\n\n")

    # Generate final response from index, sorted by date
    final_response = []
    for date in sorted(entries_by_date.keys()):
        for _, entry in entries_by_date[date].items():
            if component and entry["component"] != component:
                continue
            final_response.append(entry)

    return final_response


@ttl_lru_cache(seconds_to_live=3600)
def query_total_costs_per_user(
    date_range: DateRange,
    hub: str = None,
    component: str = None,
    user: str = None,
    usergroup: str = None,
    limit: str = None,
):
    """
    Query total costs per user by combining AWS costs with Prometheus usage data.

    This function calculates individual user costs by:
    1. Getting total AWS costs per component (compute, home storage) from Cost Explorer
    2. Getting usage fractions per user from Prometheus metrics
    3. Multiplying total costs by each user's usage fraction

    Excludes hubs with no users (e.g., binder hubs)

    Args:
        date_range: DateRange object containing the time period for the query
        hub: The hub namespace to query (optional, if None queries all hubs)
        component: The component to query (optional, if None queries all components)
        user: The user to query (optional, if None queries all users)
        usergroup: The user group to query (optional, if None queries all user groups)
        limit: Limit number of results to top N users by total cost (optional, if None returns all users)

    Returns:
        List of dicts with keys: date, hub, component, user, value (cost in USD)
        Results are sorted by date, hub, component, then value (highest cost first)
    """
    # Get AWS cost data using the DateRange object
    costs_per_component = query_total_costs_per_component(date_range, hub)

    costs_by_date = {}
    for entry in costs_per_component:
        costs_by_date.setdefault(entry["date"], {})[entry["component"]] = float(
            entry["cost"]
        )

    # Get user usage percentages from Prometheus using the same DateRange object
    # This ensures we query the same logical date range for both AWS and Prometheus,
    # accounting for their different date range semantics (exclusive vs inclusive)
    usage_shares = query_usage(
        date_range,
        hub_name=hub,
        component_name=component,
        user_name=user,
    )

    results = []
    for entry in usage_shares:
        date = entry["date"]
        component = entry["component"]
        usage_share = entry["value"]
        if date in costs_by_date and component in costs_by_date[date]:
            total_cost_for_component = costs_by_date[date][component]
            entry["value"] = round(
                usage_share * total_cost_for_component, 4
            )  # Adjust usage share to cost
            results.append(entry)
    results = [x for x in results if x["hub"] != "binder"]  # Exclude binder hubs
    user_groups = query_user_groups(date_range, hub, user)
    list_groups = []
    for r in results:
        for entry in user_groups:
            if (r["date"] == entry["date"]) and (r["hub"] == entry["hub"]):
                if "usergroup" not in r.keys():
                    r["usergroup"] = entry["usergroup"]
                else:
                    r_copy = copy.deepcopy(r)
                    r_copy["usergroup"] = entry["usergroup"]
                    list_groups.append(r_copy)
    logger.debug(f"List groups: {list_groups}")
    results.extend(list_groups)
    if limit:
        limit = int(limit)
        user_costs = {}
        for entry in results:
            user_key = (entry["hub"], entry["user"])
            user_costs[user_key] = user_costs.get(user_key, 0) + entry["value"]
        top_users = sorted(user_costs.items(), key=lambda x: -x[1])[:limit]
        top_user_set = {user for user, _ in top_users}
        results = [
            entry for entry in results if (entry["hub"], entry["user"]) in top_user_set
        ]
    results = _filter_json(
        results, hub=hub, component=component, user=user, usergroup=usergroup
    )
    results.sort(
        key=lambda x: (x["date"], x["hub"], x["component"], -float(x["value"]))
    )
    return results
