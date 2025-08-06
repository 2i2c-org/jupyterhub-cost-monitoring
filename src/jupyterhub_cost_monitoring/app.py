from datetime import datetime, timedelta, timezone

from flask import Flask, render_template_string, request, url_for

from .logs import get_logger
from .query_cost_aws import (
    query_hub_names,
    query_total_costs,
    query_total_costs_per_component,
    query_total_costs_per_hub,
)

app = Flask(__name__)
logger = get_logger(__name__)


def _parse_from_to_in_query_params():
    """
    Parse "from" and "to" query parameters, expected to be passed as YYYY-MM-DD
    formatted strings or including time as well.

    - "to" defaults to current date (UTC)
    - "from" defaults to 30 days before what to is set to

    Note that Python 3.11 is required to parse a datetime like
    2024-07-27T15:50:18.231Z with a Z in the end, and that Grafana's
    `${__from:date}` variable is UTC based, but as soon as its adjusted with a
    custom format, it no longer is UTC based. Due to that, we need to be able to
    parse the full datetime string.
    """
    now_date = datetime.now(timezone.utc).date()
    if request.args.get("to"):
        to_date = datetime.fromisoformat(request.args["to"]).date()
    else:
        to_date = now_date
    if request.args.get("from"):
        from_date = datetime.fromisoformat(request.args["from"]).date()
    else:
        from_date = to_date - timedelta(days=30)

    # the to_date isn't included when declaring start/end dates against the AWS
    # CE API, so we try to add one day to it to make it inclusive
    to_date = to_date + timedelta(days=1)
    # prevent "end date past the beginning of next month" errors
    if to_date > now_date:
        to_date = now_date
    # prevent "Start date (and hour) should be before end date (and hour)"
    if from_date >= now_date:
        from_date = to_date - timedelta(days=1)

    # format back to YYYY-MM-DD strings
    from_date = from_date.strftime("%Y-%m-%d")
    to_date = to_date.strftime("%Y-%m-%d")

    return from_date, to_date


@app.route("/")
def index():
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
    return ("200: OK", 200)


@app.route("/hub-names")
def hub_names():
    from_date, to_date = _parse_from_to_in_query_params()

    return query_hub_names(from_date, to_date)


@app.route("/total-costs")
def total_costs():
    from_date, to_date = _parse_from_to_in_query_params()

    return query_total_costs(from_date, to_date)


@app.route("/total-costs-per-hub")
def total_costs_per_hub():
    from_date, to_date = _parse_from_to_in_query_params()

    return query_total_costs_per_hub(from_date, to_date)


@app.route("/total-costs-per-component")
def total_costs_per_component():
    from_date, to_date = _parse_from_to_in_query_params()
    hub_name = request.args.get("hub")

    return query_total_costs_per_component(from_date, to_date, hub_name)
