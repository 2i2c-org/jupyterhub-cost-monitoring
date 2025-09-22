from src.jupyterhub_cost_monitoring.const_usage import USAGE_MAP
from src.jupyterhub_cost_monitoring.date_utils import parse_from_to_in_query_params
from src.jupyterhub_cost_monitoring.logs import get_logger
from src.jupyterhub_cost_monitoring.query_usage import query_prometheus

logger = get_logger(__name__)

date_range = parse_from_to_in_query_params(
    from_date="2025-08-20", to_date="2025-09-20"
)  # Test date range used to generate JSON data


def test_get_usage_data(mock_usage_response):
    component_name = mock_usage_response.test_param.replace("_", " ")
    logger.debug(f"Running with param: {component_name}")
    response = query_prometheus(
        USAGE_MAP[component_name]["query"],
        date_range,
        step=USAGE_MAP[component_name]["step"],
    )
    assert response["status"] == "success"
