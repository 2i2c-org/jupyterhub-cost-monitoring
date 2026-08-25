import json
from pathlib import Path

from pytest_httpserver import HTTPServer
from traitlets.config import Application

from jupyterhub_cost_monitoring.aws import AWSCostExplorer
from jupyterhub_cost_monitoring.date_utils import DateRange

from .utils import setup_mock_ce


def test_query_account_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/data/fixtures/aws-ce/test_query_account_cost-input.json"),
    )

    account_costs = ce.query_account_costs(aws_date_range)
    with open("tests/data/fixtures/aws-ce/test_query_account_cost-output.json") as f:
        assert account_costs == json.load(f)


def test_query_attributable_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/data/fixtures/aws-ce/test_query_attributable_cost-input.json"),
    )

    account_costs = ce.query_attributable_costs(aws_date_range)
    with open(
        "tests/data/fixtures/aws-ce/test_query_attributable_cost-output.json"
    ) as f:
        assert account_costs == json.load(f)


def test_query_hub_names(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver, Path("tests/data/fixtures/aws-ce/test_query_hub_names-input.json")
    )

    hub_names = ce.query_hub_names(aws_date_range)

    with open("tests/data/fixtures/aws-ce/test_query_hub_names-output.json") as f:
        assert hub_names == json.load(f)


def test_query_total_costs_per_hub(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(
        httpserver,
        Path("tests/data/fixtures/aws-ce/test_query_total_costs_per_hub-input.json"),
    )

    per_hub_costs = ce.query_total_costs_per_hub(aws_date_range)
    with open(
        "tests/data/fixtures/aws-ce/test_query_total_costs_per_hub-output.json"
    ) as f:
        assert per_hub_costs == json.load(f)


def test_query_total_costs_per_component(
    httpserver: HTTPServer, aws_date_range: DateRange
):
    ce = setup_mock_ce(
        httpserver,
        [
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component-input_by_service.json"
            ),
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component-input_homedir.json"
            ),
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component-input_core.json"
            ),
        ],
    )

    with open(
        "tests/data/fixtures/aws-ce/test_query_total_costs_per_component-output.json"
    ) as f:
        assert ce.query_total_costs_per_component(aws_date_range) == json.load(f)


def test_query_total_costs_per_component_per_hub(
    httpserver: HTTPServer, aws_date_range: DateRange
):
    ce = setup_mock_ce(
        httpserver,
        [
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component_per_hub-input_by_service.json"
            ),
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component_per_hub-input_homedir.json"
            ),
            Path(
                "tests/data/fixtures/aws-ce/test_query_total_costs_per_component_per_hub-input_core.json"
            ),
        ],
    )


    with open(
        "tests/data/fixtures/aws-ce/test_query_total_costs_per_component_per_hub-output.json"
    ) as f:
        assert ce.query_total_costs_per_component(aws_date_range, hub_name="prod") == json.load(f)
