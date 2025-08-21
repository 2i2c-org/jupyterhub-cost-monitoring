from datetime import datetime, timedelta, timezone

from flask import Flask, render_template_string, request, url_for

from .logs import get_logger
from .query_cost_aws import (
    query_hub_names,
    query_total_costs,
    query_total_costs_per_component,
    query_total_costs_per_hub,
    query_total_costs_per_user,
)
from .query_usage import query_usage

app = Flask(__name__)
logger = get_logger(__name__)


def _parse_from_to_in_query_params(api_provider: str = "prometheus"):
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
    if request.args.get("to"):
        to_date = datetime.fromisoformat(request.args["to"])
    else:
        to_date = now_date
    if request.args.get("from"):
        from_date = datetime.fromisoformat(request.args["from"])
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


@app.route("/")
def index():
    """
    Index page that lists all available endpoints in the application.
    """
    links = []
    for rule in app.url_map.iter_rules():
        # Skip static routes and those requiring parameters
        if rule.endpoint != "static" and len(rule.arguments) == 0:
            url = url_for(rule.endpoint)
            links.append((rule.endpoint, url))

    # Render links using a simple HTML template
    return render_template_string(
        """
        <h1>Available Endpoints</h1>
        <ul>
        {% for endpoint, url in links %}
            <li><a href="{{ url }}">{{ endpoint }}</a></li>
        {% endfor %}
        </ul>
    """,
        links=links,
    )


@app.route("/health/ready")
def ready():
    """
    Readiness probe endpoint.
    """
    return ("200: OK", 200)


@app.route("/hub-names")
def hub_names():
    """
    Endpoint to query hub names.
    """
    from_date, to_date = _parse_from_to_in_query_params(api_provider="aws")

    return query_hub_names(from_date, to_date)


@app.route("/total-costs")
def total_costs():
    """
    Endpoint to query total costs.
    """
    from_date, to_date = _parse_from_to_in_query_params(api_provider="aws")

    return query_total_costs(from_date, to_date)


@app.route("/total-costs-per-hub")
def total_costs_per_hub():
    """
    Endpoint to query total costs per hub.
    """
    from_date, to_date = _parse_from_to_in_query_params(api_provider="aws")

    return query_total_costs_per_hub(from_date, to_date)


@app.route("/total-costs-per-component")
def total_costs_per_component():
    """
    Endpoint to query total costs per component.
    """
    from_date, to_date = _parse_from_to_in_query_params(api_provider="aws")
    hub_name = request.args.get("hub")
    component = request.args.get("component")

    return query_total_costs_per_component(from_date, to_date, hub_name, component)


@app.route("/costs-per-user")
def costs_per_user():
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
    from_date, to_date = _parse_from_to_in_query_params(api_provider="aws")
    hub_name = request.args.get("hub")
    component = request.args.get("component")
    user = request.args.get("user")
    # Grafana will pass empty string to get data for all hubs,
    # so we need to handle that case.
    if not hub_name:
        hub_name = None
    if not component:
        component = None
    if not user:
        user = None

    # Get per-user costs by combining AWS costs with Prometheus usage data
    per_user_costs = query_total_costs_per_user(
        from_date, to_date, hub_name, component, user
    )

    return per_user_costs


@app.route("/total-usage")
def total_usage():
    """
    Endpoint to query total usage.
    Expects 'from' and 'to' query parameters in the api_provider YYYY-MM-DD.
    Optionally accepts 'hub', 'component' and 'user', query parameters.
    """
    from_date, to_date = _parse_from_to_in_query_params(api_provider="prometheus")
    hub_name = request.args.get("hub")
    component_name = request.args.get("component")
    user_name = request.args.get("user")

    return query_usage(from_date, to_date, hub_name, component_name, user_name)
