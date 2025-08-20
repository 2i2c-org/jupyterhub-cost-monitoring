import json

import pytest


@pytest.fixture(scope="session")
def input_data_usage():
    with open("tests/test_data_usage.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="session")
def input_data_cost():
    with open("tests/test_data_cost.json") as f:
        data = json.load(f)
    return data
