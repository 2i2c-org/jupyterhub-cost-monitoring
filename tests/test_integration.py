from collections import defaultdict

import pytest

from src.jupyterhub_cost_monitoring.const_cost_aws import (
    GRANULARITY_DAILY,
    METRICS_UNBLENDED_COST,
)
from src.jupyterhub_cost_monitoring.date_utils import parse_from_to_in_query_params
from src.jupyterhub_cost_monitoring.logs import get_logger
from src.jupyterhub_cost_monitoring.query_cost_aws import (
    query_total_costs_per_component,
)

logger = get_logger(__name__)

date_range = parse_from_to_in_query_params("2025-09-01", "2025-09-02")


@pytest.mark.parametrize(
    "mock_prometheus_usage", [["compute", "home_storage"]], indirect=True
)
def test_get_usage_data(mock_prometheus_usage, env_vars):
    """
    Test mocked Prometheus compute and home storage json data retrieval.
    """
    from src.jupyterhub_cost_monitoring.query_usage import query_usage

    for component_name in ["compute", "home_storage"]:
        response = query_usage(
            date_range,
            hub_name=None,
            component_name=component_name,
            user_name=None,
        )
        logger.info(f"{component_name} usage shares: {response}")
        assert len(response) > 0


def test_get_user_group_info(mock_prometheus_user_group_info, env_vars):
    """
    Test mocked Prometheus user group info json data retrieval.
    """
    from src.jupyterhub_cost_monitoring.query_usage import query_user_groups

    response = query_user_groups(
        date_range,
        hub_name=None,
        user_name=None,
        group_name=None,
    )
    logger.info(f"User group info: {response}")
    assert len(response) > 0


def test_get_cost_component_data(mock_ce, env_vars):
    """
    Test mocked AWS Cost Explorer cost json data retrieval for all, home storage and core components.
    """
    from_date, to_date = date_range.aws_range
    params = {
        "TimePeriod": {"Start": f"{from_date}", "End": f"{to_date}"},
        "Granularity": GRANULARITY_DAILY,
        "Metrics": [METRICS_UNBLENDED_COST],
    }
    for i in range(3):
        # range(3) to cover stubbed responses for all, home storage and core costs
        response = mock_ce.get_cost_and_usage(
            TimePeriod=params["TimePeriod"],
            Granularity=params["Granularity"],
            Metrics=params["Metrics"],
        )
        logger.debug(f"Cost response {i + 1}: {response}")
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_total_costs_per_component(mock_ce):
    """
    Test cost logic for compute, home storage and core components of the total costs per component endpoint.
    """
    costs_per_component = query_total_costs_per_component(date_range)
    components = {"compute", "home storage", "core"}
    logger.info(f"Costs per component: {costs_per_component}")

    result = {
        item["component"]: float(item["cost"])
        for item in costs_per_component
        if item["date"] == date_range.aws_range[0] and item["component"] in components
    }

    assert result["compute"] == 8.85
    assert result["home storage"] == 7.22
    assert result["core"] == 11.13


@pytest.mark.parametrize("mock_prometheus_usage", [None], indirect=True)
def test_costs_per_user(
    mock_prometheus_usage,
    mock_prometheus_usage_share,
    mock_prometheus_user_group_info,
    mock_ce,
    output_cost_per_user,
):
    """
    Test cost logic for cost-per-user endpoint.
    """
    from src.jupyterhub_cost_monitoring.query_cost_aws import query_total_costs_per_user

    result = query_total_costs_per_user(date_range)
    logger.info(f"Cost per user: {result}")

    lookup = {
        (o["date"], o["user"], o["component"], o["hub"]): o["value"]
        for o in output_cost_per_user
    }

    for r in result:
        key = (r["date"], r["user"], r["component"], r["hub"])
        if key in lookup:
            assert r["value"] == lookup[key]


@pytest.mark.parametrize("mock_prometheus_usage", [None], indirect=True)
def test_costs_per_user_limit(
    mock_ce,
    mock_prometheus_usage,
    mock_prometheus_usage_share,
    mock_prometheus_user_group_info,
    output_cost_per_user,
):
    """
    Test cost logic for cost-per-user endpoint with limit parameter.
    """
    from src.jupyterhub_cost_monitoring.query_cost_aws import query_total_costs_per_user

    limit = 2
    result = query_total_costs_per_user(date_range, limit=limit)
    users = {r["user"] for r in result}

    assert len(users) == limit

    per_user = defaultdict(float)
    for row in result:
        per_user[row["user"]] += row["value"]
    sorted_users = sorted(per_user.items(), key=lambda x: x[1], reverse=True)
    top_sum = sum(v for _, v in sorted_users[:limit])

    assert round(top_sum, 2) == 20.50
