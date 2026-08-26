import json
import logging
from datetime import timedelta
from pathlib import Path

from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.const_usage import USAGE_MAP, USER_GROUP_INFO
from jupyterhub_cost_monitoring.date_utils import (
    DateRange,
    get_now_date,
    parse_from_to_in_query_params,
)
from jupyterhub_cost_monitoring.prometheus import Prometheus

from .utils import mock_prometheus_queries

logger = logging.getLogger(__name__)

date_range = parse_from_to_in_query_params("2025-09-01", "2025-09-02")


def test_get_user_group_info(httpserver: HTTPServer):
    """
    Test mocked Prometheus user group info json data retrieval.
    """

    prometheus = Prometheus()
    prometheus.host = httpserver.host
    prometheus.port = httpserver.port

    now_date = get_now_date() - timedelta(days=1)

    date_range = DateRange(start_date=now_date, end_date=now_date)
    start, end = date_range.prometheus_range

    mock_prometheus_queries(
        httpserver,
        [
            {
                "query": USER_GROUP_INFO,
                "start": start,
                "end": end,
                "step": "1d",
                "response": Path("tests/data/prometheus-groups.json"),
            }
        ],
    )

    response = prometheus.query_user_groups(
        date_range,
        hub_name=None,
        user_name=None,
        group_name=None,
    )

    with open("tests/data/test_output_user_group_info.json") as f:
        expected_response = json.load(f)
        assert expected_response == response


def test_get_usage_data(httpserver: HTTPServer):
    prometheus = Prometheus()

    prometheus.host = httpserver.host
    prometheus.port = httpserver.port

    now_date = get_now_date() - timedelta(days=1)

    date_range = DateRange(start_date=now_date, end_date=now_date)
    start, end = date_range.prometheus_range
    mock_prometheus_queries(
        httpserver,
        [
            {
                "query": USAGE_MAP[component]["query"],
                "start": start,
                "end": end,
                "step": USAGE_MAP[component]["step"],
                "response": Path(
                    f"tests/data/prometheus-responses/{component.replace(' ', '-')}-usage.json"
                ),
            }
            for component in ["compute", "home storage"]
        ],
    )
    response = prometheus.query_usage(
        date_range,
        hub_name=None,
        component_name=None,
        user_name=None,
    )

    with open("tests/data/test_get_usage_data_output.json") as f:
        expected_data = json.load(f)
        assert expected_data == response
