from src.jupyterhub_cost_monitoring.const_cost_aws import (
    GRANULARITY_DAILY,
    METRICS_UNBLENDED_COST,
)
from src.jupyterhub_cost_monitoring.const_usage import USAGE_MAP
from src.jupyterhub_cost_monitoring.logs import get_logger
from src.jupyterhub_cost_monitoring.query_usage import query_prometheus

logger = get_logger(__name__)


def test_get_usage_data(mock_usage_response, sample_date_range):
    """
    Test mocked Prometheus compute and home storage json data retrieval.
    """
    component_name = mock_usage_response.test_param.replace("_", " ")
    logger.debug(f"Running with param: {component_name}")
    date_range = sample_date_range
    response = query_prometheus(
        USAGE_MAP[component_name]["query"],
        date_range,
        step=USAGE_MAP[component_name]["step"],
    )
    logger.debug(f"Usage response: {response}")
    assert response["status"] == "success"


def test_get_cost_component(mock_ce, sample_date_range):
    """
    Test mocked AWS Cost Explorer cost json data retrieval for all, home storage and core components.
    """
    from_date, to_date = sample_date_range.aws_range
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
