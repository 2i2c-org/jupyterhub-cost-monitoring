import json
import logging
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import TypedDict

import pytest
from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.const_cost_aws import (
    GRANULARITY_DAILY,
    METRICS_UNBLENDED_COST,
)
from jupyterhub_cost_monitoring.const_usage import USAGE_MAP, USER_GROUP_INFO
from jupyterhub_cost_monitoring.date_utils import (
    DateRange,
    get_now_date,
    parse_from_to_in_query_params,
)
from jupyterhub_cost_monitoring.prometheus import Prometheus

logger = logging.getLogger(__name__)

date_range = parse_from_to_in_query_params("2025-09-01", "2025-09-02")


MockedQueryResponse = TypedDict(
    "MockedQueryResponse",
    {"query": str, "start": str, "end": str, "step": str, "response": str | Path},
)


def mock_prometheus_queries(
    httpserver: HTTPServer, query_responses: list[MockedQueryResponse]
):
    for query_response in query_responses:
        if isinstance(query_response["response"], Path):
            with open(query_response["response"]) as f:
                response = f.read()
        else:
            response = query_response["response"]

        httpserver.expect_request(
            "/api/v1/query_range",
            query_string={
                "query": query_response["query"],
                "start": query_response["start"],
                "end": query_response["end"],
                "step": query_response["step"],
            },
        ).respond_with_data(response)


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
def test_costs_per_group(
    mock_prometheus_usage,
    mock_prometheus_usage_share,
    mock_prometheus_user_group_info,
    mock_ce,
    output_cost_per_group,
):
    """
    Test cost logic for costs per group.
    """
    from src.jupyterhub_cost_monitoring.query_cost_aws import (
        query_total_costs_per_group,
    )

    result = query_total_costs_per_group(date_range)
    logger.info(f"Cost per group: {result}")

    lookup = {(o["date"], o["usergroup"]): o["cost"] for o in output_cost_per_group}

    for r in result:
        key = (r["date"], r["usergroup"])
        if key in lookup:
            assert r["cost"] == lookup[key]


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
