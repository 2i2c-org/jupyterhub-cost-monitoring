from fastapi import FastAPI, Query

from .const_usage import USAGE_MAP
from .date_utils import parse_from_to_in_query_params
from .logs import get_logger
from .query_cost_aws import (
    query_hub_names,
    query_total_costs,
    query_total_costs_per_component,
    query_total_costs_per_hub,
    query_total_costs_per_user,
)
from .query_usage import query_usage, query_user_groups

app = FastAPI()
logger = get_logger(__name__)


@app.get("/")
def index():
    return {"message": "Welcome to the JupyterHub Cost Monitoring API"}


@app.get("/health/ready")
def ready():
    """
    Readiness probe endpoint.
    """
    return ("200: OK", 200)


@app.get("/hub-names")
def hub_names(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
):
    """
    Endpoint to query hub names.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    return query_hub_names(date_range)


@app.get("/component-names")
def component_names():
    """
    Endpoint to serve component names.
    """
    return list(USAGE_MAP.keys())


@app.get("/total-costs")
def total_costs(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
):
    """
    Endpoint to query total costs.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    return query_total_costs(date_range)


@app.get("/user-groups")
def user_groups(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    username: str | None = Query(
        None, description="Name of the user to filter results"
    ),
    usergroup: str | None = Query(
        None, description="Name of the group to filter results"
    ),
):
    """
    Endpoint to serve user group memberships.
    """
    date_range = parse_from_to_in_query_params(from_date, to_date)

    return query_user_groups(date_range, hub, username, usergroup)


@app.get("/total-costs-per-hub")
def total_costs_per_hub(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
):
    """
    Endpoint to query total costs per hub.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    return query_total_costs_per_hub(date_range)


@app.get("/total-costs-per-component")
def total_costs_per_component(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    component: str | None = Query(
        None, description="Name of the component to filter results"
    ),
):
    """
    Endpoint to query total costs per component.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    if not hub or hub.lower() == "all":
        hub = None
    if not component or component.lower() == "all":
        component = None

    return query_total_costs_per_component(date_range, hub, component)


@app.get("/costs-per-user")
def costs_per_user(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    component: str | None = Query(
        None, description="Name of the component to filter results"
    ),
    user: str | None = Query(None, description="Name of the user to filter results"),
    usergroup: str | None = Query(
        None, description="Name of user group to filter results"
    ),
    limit: str | None = Query(
        None, description="Limit number of results to top N users by total cost."
    ),
):
    """
    Endpoint to query costs per user by combining AWS costs with Prometheus usage data.

    This endpoint calculates individual user costs by:
    1. Getting total AWS costs per component (compute, storage) from Cost Explorer
    2. Getting usage fractions per user from Prometheus metrics
    3. Multiplying total costs by each user's usage fraction

    Query Parameters:
        from (str): Start date in YYYY-MM-DD format (defaults to 30 days ago)
        to (str): End date in YYYY-MM-DD format (defaults to current date)
        hub (str, optional): Filter to specific hub namespace
        component (str, optional): Filter to specific component (compute, home storage)
        user (str, optional): Filter to specific user
        usergroup (str, optional): Filter to specific user group
        limit (int, optional): Limit number of results to top N users by total cost.

    Returns:
        List of dicts with keys: date, hub, component, user, value (cost in USD)
        Results are sorted by date, hub, component, then value (highest cost first)
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)
    usergroup = usergroup.strip("{}").split(",")

    if not hub or hub.lower() == "all":
        hub = None
    if not component or component.lower() == "all":
        component = None
    if not user or user.lower() == "all":
        user = None
    if not limit or (str(limit).lower() == "all"):
        limit = None
    if not usergroup or ("all" in [u.lower() for u in usergroup]):
        usergroup = [None]

    logger.info(f"Limit parameter: {limit}")

    # Get per-user costs by combining AWS costs with Prometheus usage data
    results = []
    for ug in usergroup:
        per_user_costs = query_total_costs_per_user(
            date_range, hub, component, user, ug, limit
        )
        results.extend(per_user_costs)

    return results


@app.get("/total-usage")
def total_usage(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    component: str | None = Query(
        None, description="Name of the component to filter results"
    ),
    user: str | None = Query(None, description="Name of the user to filter results"),
):
    """
    Endpoint to query total usage.
    Expects 'from' and 'to' query parameters in the api_provider YYYY-MM-DD.
    Optionally accepts 'hub', 'component' and 'user', query parameters.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    if not hub or hub.lower() == "all":
        hub = None
    if not component or component.lower() == "all":
        component = None
    if not user or user.lower() == "all":
        user = None

    return query_usage(date_range, hub, component, user)
