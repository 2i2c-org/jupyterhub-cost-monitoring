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


def test_get_usage_data(mock_prometheus, env_vars):
    """
    Test mocked Prometheus compute and home storage json data retrieval.
    """
    from src.jupyterhub_cost_monitoring.query_usage import query_usage

    component_name = mock_prometheus.test_param.replace("_", " ")
    response = query_usage(
        date_range,
        hub_name=None,
        component_name=component_name,
        user_name=None,
    )
    logger.info(f"{component_name} usage shares: {response}")
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


def test_total_costs_per_component(mock_ce, env_vars):
    """
    Test cost logic for compute, home storage and core components of the total costs per component endpoint.
    """
    costs_per_component = query_total_costs_per_component(date_range)
    components = {"compute", "home storage", "core"}

    result = {
        item["component"]: float(item["cost"])
        for item in costs_per_component
        if item["date"] == date_range.aws_range[0] and item["component"] in components
    }

    assert result["compute"] == 8.85
    assert result["home storage"] == 7.22
    assert result["core"] == 11.13


def test_costs_per_user(mock_prometheus, mock_ce):
    from src.jupyterhub_cost_monitoring.query_cost_aws import query_total_costs_per_user

    result = query_total_costs_per_user(date_range)
    logger.debug(f"Costs per user result: {result}")
