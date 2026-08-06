import json
from datetime import datetime
from pathlib import Path
from typing import List

import pytest
from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.aws import AWSCostExplorer
from jupyterhub_cost_monitoring.date_utils import DateRange


@pytest.fixture
def aws_date_range() -> DateRange:
    return DateRange(datetime(2026, 6, 20), datetime(2026, 6, 27))


def setup_mock_ce(httpserver: HTTPServer, responses: Path | List[Path]):

    aws_endpoint_url = f"http://{httpserver.host}:{httpserver.port}/"
    ce = AWSCostExplorer(
        aws_client_extra_kwargs={
            "region_name": "test",  # does not matter but we must pass it
            "endpoint_url": aws_endpoint_url,
        }
    )

    if isinstance(responses, Path):
        paths = [responses]
    else:
        paths = responses

    for path in paths:
        with open(path) as f:
            httpserver.expect_ordered_request("/", method="POST").respond_with_data(
                f.read()
            )

    return ce


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
