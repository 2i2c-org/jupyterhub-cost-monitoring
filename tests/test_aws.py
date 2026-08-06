import json
from datetime import datetime
from pathlib import Path

import pytest
from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.aws import AWSCostExplorer
from jupyterhub_cost_monitoring.date_utils import DateRange


@pytest.fixture
def aws_date_range() -> DateRange:
    return DateRange(datetime(2026, 6, 20), datetime(2026, 6, 27))


def setup_mock_ce(httpserver: HTTPServer, response: str | Path):

    aws_endpoint_url = f"http://{httpserver.host}:{httpserver.port}/"
    ce = AWSCostExplorer(
        aws_client_extra_kwargs={
            "region_name": "test", # does not matter but we must pass it
            "endpoint_url": aws_endpoint_url,
        }
    )

    if isinstance(response, Path):
        with open(response) as f:
            expected_response = f.read()
    else:
        expected_response = response

    httpserver.expect_request("/", method="POST").respond_with_data(expected_response)
    return ce

def test_query_account_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(httpserver, Path("tests/data/fixtures/aws-ce/test_query_account_cost-input.json"))

    account_costs = ce.query_account_costs(aws_date_range)
    with open("tests/data/fixtures/aws-ce/test_query_account_cost-output.json") as f:
        assert account_costs == json.load(f)


def test_query_attributable_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    ce = setup_mock_ce(httpserver, Path("tests/data/fixtures/aws-ce/test_query_attributable_cost-input.json"))

    account_costs = ce.query_attributable_costs(aws_date_range)
    with open(
        "tests/data/fixtures/aws-ce/test_query_attributable_cost-output.json"
    ) as f:
        assert account_costs == json.load(f)
