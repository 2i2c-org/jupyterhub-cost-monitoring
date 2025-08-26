from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Query

from .const_usage import USAGE_MAP
from .logs import get_logger
from .query_cost_aws import (
    query_hub_names,
    query_total_costs,
    query_total_costs_per_component,
    query_total_costs_per_hub,
    query_total_costs_per_user,
)
from .query_usage import query_usage

app = FastAPI()
logger = get_logger(__name__)


def _parse_from_to_in_query_params(
    from_date: str | None = None,
    to_date: str | None = None,
    api_provider: str = "prometheus" or "aws" or None,
):
    """
    Parse "from" and "to" query parameters, expected to be passed as YYYY-MM-DD
    api_providerted strings or including time as well.

    Args:
        api_provider (str): The api_provider, such as "prometheus" or "aws". Formats dates accordingly.

    - "to" defaults to current date (UTC)
    - "from" defaults to 30 days prior to the "to" date

    Returns:
        from_date and to_date as datetime.date objects, or their string api_providers, according to the `api_provider` argument.

    Note that Python 3.11 is required to parse a datetime like
    2024-07-27T15:50:18.231Z with a Z in the end, and that Grafana's
    `${__from:date}` variable is UTC based, but as soon as its adjusted with a
    custom api_provider, it no longer is UTC based. Due to that, we need to be able to
    parse the full datetime string.
    """
    now_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if to_date:
        to_date = datetime.fromisoformat(to_date)
    else:
        to_date = now_date
    if from_date:
        from_date = datetime.fromisoformat(from_date)
    else:
        from_date = to_date - timedelta(days=30)

    # prevent "end date past the beginning of next month" errors
    if to_date > now_date:
        to_date = now_date
    # prevent "Start date (and hour) should be before end date (and hour)"
    if from_date >= now_date:
        from_date = to_date - timedelta(days=1)

    if api_provider == "prometheus":
        return from_date.isoformat(), to_date.isoformat()
    else:
        # "aws" to_dates are exclusive, so we add one day to include it
        to_date = to_date + timedelta(days=1)
        from_date = from_date.strftime("%Y-%m-%d")
        to_date = to_date.strftime("%Y-%m-%d")
        return from_date, to_date


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
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="aws"
    )

    return query_hub_names(from_date, to_date)


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
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="aws"
    )

    return query_total_costs(from_date, to_date)


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
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="aws"
    )

    return query_total_costs_per_hub(from_date, to_date)


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
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="aws"
    )

    return query_total_costs_per_component(from_date, to_date, hub, component)


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

    Returns:
        List of dicts with keys: date, hub, component, user, value (cost in USD)
        Results are sorted by date, hub, component, then value (highest cost first)
    """
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="aws"
    )
    if not hub or hub == "all":
        hub = None
    if not component or component == "all":
        component = None
    if not user or user == "all":
        user = None

    # Get per-user costs by combining AWS costs with Prometheus usage data
    per_user_costs = query_total_costs_per_user(
        from_date, to_date, hub, component, user
    )

    return per_user_costs


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
    from_date, to_date = _parse_from_to_in_query_params(
        from_date, to_date, api_provider="prometheus"
    )

    return query_usage(from_date, to_date, hub, component, user)
