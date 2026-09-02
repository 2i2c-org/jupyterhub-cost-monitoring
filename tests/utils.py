from pathlib import Path
from typing import List, TypedDict

from botocore import UNSIGNED
from botocore.config import Config
from pytest_httpserver import HTTPServer

from jupyterhub_cost_monitoring.aws import AWSCostExplorer

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


def setup_mock_ce(httpserver: HTTPServer, responses: Path | List[Path]):

    aws_endpoint_url = f"http://{httpserver.host}:{httpserver.port}/"
    ce = AWSCostExplorer(
        aws_client_extra_kwargs={
            "region_name": "test",  # does not matter but we must pass it
            "endpoint_url": aws_endpoint_url,
            # Don't try to sign our requests, since our fake HTTP server doesn't support that
            "config": Config(signature_version=UNSIGNED),
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
