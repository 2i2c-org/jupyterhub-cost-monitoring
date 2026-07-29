import json
from datetime import datetime

import pytest
from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.aws import AWSCostExplorer
from jupyterhub_cost_monitoring.date_utils import DateRange


@pytest.fixture
def aws_date_range() -> DateRange:
    return DateRange(datetime(2026, 6, 20), datetime(2026, 6, 27))


def test_query_account_cost(httpserver: HTTPServer, aws_date_range: DateRange):
    aws_endpoint_url = f"http://{httpserver.host}:{httpserver.port}/"
    ce = AWSCostExplorer(
        aws_client_extra_kwargs={
            "region_name": "test",
            "endpoint_url": aws_endpoint_url,
        }
    )

    with open("tests/data/fixtures/aws-ce/test_query_account_cost-input.json") as f:
        httpserver.expect_request("/", method="POST").respond_with_data(f.read())

    account_costs = ce.query_account_costs(aws_date_range)
    with open("tests/data/fixtures/aws-ce/test_query_account_cost-output.json") as f:
        assert account_costs == json.load(f)
