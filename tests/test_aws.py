import json
from pathlib import Path

from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.const_usage import USAGE_MAP, USER_GROUP_INFO
from jupyterhub_cost_monitoring.date_utils import DateRange
from jupyterhub_cost_monitoring.prometheus import Prometheus

from .utils import mock_prometheus_queries, setup_mock_ce


def test_query_account_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/fixtures/aws-ce/test_query_account_cost/input.json"),
    )

    account_costs = ce.query_account_costs(aws_date_range)
    with open("tests/fixtures/aws-ce/test_query_account_cost/output.json") as f:
        assert account_costs == json.load(f)


def test_query_attributable_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/fixtures/aws-ce/test_query_attributable_cost/input.json"),
    )

    account_costs = ce.query_attributable_costs(aws_date_range)
    with open("tests/fixtures/aws-ce/test_query_attributable_cost/output.json") as f:
        assert account_costs == json.load(f)


def test_query_hub_names(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver, Path("tests/fixtures/aws-ce/test_query_hub_names/input.json")
    )

    hub_names = ce.query_hub_names(aws_date_range)

    with open("tests/fixtures/aws-ce/test_query_hub_names/output.json") as f:
        assert hub_names == json.load(f)


def test_query_total_costs_per_hub(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/fixtures/aws-ce/test_query_total_costs_per_hub/input.json"),
    )

    per_hub_costs = ce.query_total_costs_per_hub(aws_date_range)
    with open("tests/fixtures/aws-ce/test_query_total_costs_per_hub/output.json") as f:
        assert per_hub_costs == json.load(f)


def test_query_total_costs_per_component(
    httpserver: HTTPServer, aws_date_range: DateRange
):
    ce = setup_mock_ce(
        httpserver,
        [
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component/input/by-service.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component/input/homedir.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component/input/core.json"
            ),
        ],
    )

    with open(
        "tests/fixtures/aws-ce/test_query_total_costs_per_component/output.json"
    ) as f:
        assert ce.query_total_costs_per_component(aws_date_range) == json.load(f)


def test_query_total_costs_per_component_per_hub(
    httpserver: HTTPServer, aws_date_range: DateRange
):
    ce = setup_mock_ce(
        httpserver,
        [
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component_per_hub/input/by-service.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component_per_hub/input/homedir.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_component_per_hub/input/core.json"
            ),
        ],
    )

    with open(
        "tests/fixtures/aws-ce/test_query_total_costs_per_component_per_hub/output.json"
    ) as f:
        assert ce.query_total_costs_per_component(
            aws_date_range, hub_name="prod"
        ) == json.load(f)


def test_query_total_costs_per_user(httpserver: HTTPServer, aws_date_range: DateRange):
    start, end = aws_date_range.prometheus_range

    prometheus = Prometheus()

    prometheus.host = httpserver.host
    prometheus.port = httpserver.port

    query_responses = [
        {
            "query": USAGE_MAP[component]["query"],
            "start": start,
            "end": end,
            "step": USAGE_MAP[component]["step"],
            "response": Path(
                f"tests/fixtures/aws-ce/test_query_total_costs_per_user/input/prometheus-{component.replace(' ', '-')}.json"
            ),
        }
        for component in ["compute", "home storage"]
    ]
    query_responses.append(
        {
            "query": USER_GROUP_INFO,
            "start": start,
            "end": end,
            "step": "1d",
            "response": Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_user/input/prometheus-groups.json"
            ),
        }
    )
    mock_prometheus_queries(httpserver, query_responses)

    ce = setup_mock_ce(
        httpserver,
        [
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_user/input/aws-ce-by-service.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_user/input/aws-ce-homedir.json"
            ),
            Path(
                "tests/fixtures/aws-ce/test_query_total_costs_per_user/input/aws-ce-core.json"
            ),
        ],
    )

    ce.prometheus = prometheus
    with open("tests/fixtures/aws-ce/test_query_total_costs_per_user/output.json") as f:
        assert json.load(f) == ce.query_total_costs_per_user(aws_date_range)
