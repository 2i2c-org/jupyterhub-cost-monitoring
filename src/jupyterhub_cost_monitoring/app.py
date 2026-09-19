import itertools
from datetime import date, timedelta

from fastapi import FastAPI, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from traitlets import Instance, Unicode
from traitlets.config import Application

from .aws import AWSCostExplorer
from .date_utils import get_now_date, parse_from_to_in_query_params
from .metrics import MetricsMiddleware
from .prometheus import Component, Prometheus


class JupyterHubCostMonitoring(Application):
    # Used as prefix for setting config values via environment variables
    # Important as `fastapi run` doesn't let us pass in variables
    # via commandline parameters
    name = "JupyterHubCostMonitoring"

    config_file = Unicode(
        "jupyterhub_cost_monitoring_config.py",
        help="""
        The config file to load.

        Can be specified with the environment variable
        `JUPYTERHUBCOSTMONITORING__JupyterHubCostMonitoring__config_file`
        """,
        config=True,
    )

    prometheus = Instance(klass=Prometheus)

    aws_ce = Instance(klass=AWSCostExplorer)

    def initialize(self, *args, **kwargs) -> None:
        super().initialize(*args, **kwargs)
        self.load_config_environ()
        self.load_config_file(self.config_file)
        self.prometheus = Prometheus(parent=self)
        self.aws_ce = AWSCostExplorer(parent=self)


app = FastAPI()
app.add_middleware(MetricsMiddleware)

# Create our traitlets app so we can specify config
jupyterhub_cost_monitoring_app = JupyterHubCostMonitoring()
jupyterhub_cost_monitoring_app.initialize()


@app.get("/")
def index():
    return {"message": "Welcome to the JupyterHub Cost Monitoring API"}


@app.get("/health/ready")
def ready():
    """
    Readiness probe endpoint.
    """
    return ("200: OK", 200)


@app.get("/hub/names")
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

    return jupyterhub_cost_monitoring_app.aws_ce.query_hub_names(date_range)


@app.get("/component-names")
def component_names():
    """
    Endpoint to serve component names.
    """
    return [Component.USER_COMPUTE, Component.USER_HOME_STORAGE]


@app.get("/totals/account")
def totals_account(
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

    account_costs = jupyterhub_cost_monitoring_app.aws_ce.query_account_costs(
        date_range
    )

    # the infinity plugin appears needs us to sort by date, otherwise it fails
    # to distinguish time series by the name field for some reason
    sorted_response = sorted(account_costs, key=lambda x: x["date"])
    return sorted_response


@app.get("/totals/attributable")
def totals_attributable(
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

    attributable_costs = jupyterhub_cost_monitoring_app.aws_ce.query_attributable_costs(
        date_range
    )

    # the infinity plugin appears needs us to sort by date, otherwise it fails
    # to distinguish time series by the name field for some reason
    sorted_response = sorted(attributable_costs, key=lambda x: x["date"])
    return sorted_response


@app.get("/user-groups")
def user_groups(
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    username: str | None = Query(
        None, description="Name of the user to filter results"
    ),
    usergroup: str | None = Query(
        None, description="Name of the group to filter results"
    ),
):
    """
    Endpoint to serve user group memberships. Note that only the most recent date for each user group membership is returned.
    """
    now_date = get_now_date() - timedelta(
        days=1
    )  # Use most recent complete day for group information
    from_date = now_date
    to_date = now_date
    date_range = parse_from_to_in_query_params(
        from_date.isoformat(), to_date.isoformat()
    )
    users = jupyterhub_cost_monitoring_app.prometheus.query_user_groups(
        date_range, hub, username, usergroup
    )

    # Flatten our users (which has nested groups) into something that Grafana can consume more easily
    return list(itertools.chain.from_iterable([u.flatten() for u in users]))


@app.get("/users-with-multiple-groups")
def users_with_multiple_groups(
    hub_name: str | None = Query(None, description="Name of the hub to filter results"),
    user_name: str | None = Query(
        None, description="Name of the user to filter results"
    ),
):
    """
    Endpoint to serve users with multiple groups.
    """
    now_date = get_now_date() - timedelta(
        days=1
    )  # Use most recent complete day for group information
    from_date = now_date
    to_date = now_date
    date_range = parse_from_to_in_query_params(
        from_date.isoformat(), to_date.isoformat()
    )

    users = jupyterhub_cost_monitoring_app.prometheus.query_user_groups(date_range)

    # FIXME: For backwards compatibility, we do two things here:
    # 1. Remove the `username_escaped` field
    # 2. Remove group named `multiple` as that is implied
    # We should break compatibility at some point

    user_entries = []
    for entry in itertools.chain.from_iterable(
        [u.flatten() for u in users if len(u.groups) > 1]
    ):
        del entry["username_escaped"]
        if entry["usergroup"] == "multiple":
            continue
        user_entries.append(entry)

    return user_entries


@app.get("/users-with-no-groups")
def users_with_no_groups(
    hub_name: str | None = Query(None, description="Name of the hub to filter results"),
    user_name: str | None = Query(
        None, description="Name of the user to filter results"
    ),
):
    """
    Endpoint to serve users with no groups.
    """
    now_date = get_now_date() - timedelta(
        days=1
    )  # Use most recent complete day for group information
    from_date = now_date
    to_date = now_date
    date_range = parse_from_to_in_query_params(
        from_date.isoformat(), to_date.isoformat()
    )

    users = jupyterhub_cost_monitoring_app.prometheus.query_user_groups(date_range)

    # FIXME: For backwards compatibility, we do two things here:
    # 1. Remove the `username_escaped` field
    # 2. Remove the `group` field
    # We should break compatibility at some point

    user_entries = []
    for entry in itertools.chain.from_iterable(
        # FIXME: We shouldn't export values with special meaning like "none" or "multiple"
        # when they can be inferred.
        [u.flatten() for u in users if u.groups == set(["none"])]
    ):
        del entry["username_escaped"]
        del entry["usergroup"]
        user_entries.append(entry)

    return user_entries


@app.get("/totals/by-hub")
def totals_by_hub(
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

    return jupyterhub_cost_monitoring_app.aws_ce.query_total_costs_per_hub(date_range)


@app.get("/hub/by-component")
def per_hub_per_component(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str = Query(None, description="Name of the hub to filter results on"),
):
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    costs_by_component = (
        jupyterhub_cost_monitoring_app.aws_ce.query_per_hub_costs_per_component(
            date_range, hub
        )
    )

    response = []

    for component, entries in costs_by_component.items():
        for ts, value in entries.items():
            response.append(
                {"component": component, "date": ts.isoformat(), "cost": value}
            )

    return sorted(response, key=lambda i: i["date"])


@app.get("/totals/by-component")
def totals_by_component(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    component: str | None = Query(
        None, description="Name of the component to filter results"
    ),
):
    """
    Endpoint to query total costs per component.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    if not component or component.lower() == "all":
        components = None
    else:
        components = [Component(component)]

    costs_by_component = (
        jupyterhub_cost_monitoring_app.aws_ce.query_total_costs_per_component(
            date_range, components
        )
    )

    response = []

    for component, entries in costs_by_component.items():
        for ts, value in entries.items():
            response.append(
                {"component": component, "date": ts.isoformat(), "cost": value}
            )

    return sorted(response, key=lambda i: i["date"])


@app.get("/total-costs-per-group")
def total_costs_per_group(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
):
    """
    Endpoint to query total costs per user group.
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)

    return jupyterhub_cost_monitoring_app.aws_ce.query_total_costs_per_group(date_range)


@app.get("/totals/by-user")
def costs_per_user(
    from_date: str | None = Query(
        None, alias="from", description="Start date in YYYY-MM-DDTHH:MMZ format"
    ),
    to_date: str | None = Query(
        None, alias="to", description="End date in YYYY-MM-DDTHH:MMZ format"
    ),
    hub: str | None = Query(None, description="Name of the hub to filter results"),
    user: str | None = Query(None, description="Name of the user to filter results"),
    usergroup: str | None = Query(
        None, description="Name of user group to filter results"
    ),
    limit: str | None = Query(
        None, description="Limit number of results to top N users by total cost."
    ),
):
    """
    Query total cost for each user for each hub, with specific filters
    """
    # Parse and validate date parameters into DateRange object
    date_range = parse_from_to_in_query_params(from_date, to_date)
    if not usergroup or ("all" in [u.lower() for u in usergroup]):
        usergroup = []

    # Get per-user costs by combining AWS costs with Prometheus usage data
    per_user_costs = jupyterhub_cost_monitoring_app.aws_ce.query_total_costs_per_user(
        date_range
    )

    # We filter after the fact. If this becomes too expensive we can
    # fix that later
    if hub and hub.casefold() != "all":
        per_user_costs = [i for i in per_user_costs if i.hub == hub]

    if user and user.casefold() != "all":
        per_user_costs = [i for i in per_user_costs if i.user == user]

    # Let's sum these
    summed_results: dict[date, dict[tuple[str, str], float]] = {}
    for p in per_user_costs:
        if p.date not in summed_results:
            summed_results[p.date] = {}
        key = (p.hub, p.user)
        summed_results[p.date][key] = summed_results[p.date].get(key, 0) + p.value

    response = []
    for ts, entries in summed_results.items():
        for (hub, username), value in entries.items():
            response.append(
                {
                    "date": ts.isoformat(),
                    "hub": hub,
                    "username": username,
                    "cost": value,
                }
            )

    if limit is not None and limit and limit.casefold() != "all" and int(limit):
        limit = int(limit)
        response = response[0 : min(limit, len(per_user_costs) - 1)]

    # FIXME: implement user group filtering

    return response


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

    return jupyterhub_cost_monitoring_app.prometheus.query_usage(
        date_range, hub, component, user
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
