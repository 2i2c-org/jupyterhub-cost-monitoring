import json

import pytest


@pytest.fixture(scope="function")
def input_data_usage():
    with open("tests/test_data_usage.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def input_data_cost():
    with open("tests/test_data_cost.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_hub():
    with open("tests/test_output_hub.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def output_data_component():
    with open("tests/test_output_component.json") as f:
        data = json.load(f)
    return data
