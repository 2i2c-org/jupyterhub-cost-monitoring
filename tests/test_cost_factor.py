import json

import numpy as np
import pandas as pd

from src.jupyterhub_cost_monitoring.app import _process_response
from src.jupyterhub_cost_monitoring.logs import get_logger
from src.jupyterhub_cost_monitoring.query_usage import calculate_cost_factor

logger = get_logger(__name__)


def generate_test_data():
    """
    Generate test data for cost factor calculation.
    """
    from_date = "2023-01-01"
    to_date = "2023-01-02"
    hubs = ["staging", "prod"]
    components = ["compute", "home-directory"]
    n_users = 3
    users = [f"user_{i}" for i in range(n_users)]
    data = []
    for hub in hubs:
        for component in components:
            for user in users:
                for date in pd.date_range(from_date, to_date):
                    data.append(
                        {
                            "date": date.strftime("%Y-%m-%d"),
                            "user": user,
                            "hub": hub,
                            "component": component,
                            "value": np.round(np.random.rand() * 10, 0),
                        }
                    )
    with open("test_data.json", "w") as f:
        json.dump(data, f, indent=4)


def test_calculate_cost_factor_by_date():
    """
    Test the cost factor function grouped by date.
    """
    with open("tests/test_data.json") as f:
        data = json.load(f)
    group_by = ["date"]
    df, group_by, filters = _process_response(data, group_by)
    result = calculate_cost_factor(df, group_by=group_by, filters=filters)
    logger.info(f"Result:\n{result}")
    with open("tests/test_output_by_date.json") as f:
        output = json.load(f)
    assert len(result) == len(output), (
        "Result length does not match expected output length"
    )
    for i in range(len(result)):
        logger.info(f"Comparing row {i}: {result.iloc[i].to_dict()} with {output[i]}")
        assert result.iloc[i].to_dict() == output[i], (
            f"Row {i} does not match expected output"
        )


def test_calculate_cost_factor_component_by_hub():
    """
    Test the cost factor function for component grouped by date and hub.
    """
    with open("tests/test_data.json") as f:
        data = json.load(f)
    group_by = ["date", "component", "hub"]  # ordering is important
    df, group_by, filters = _process_response(data, group_by)
    result = calculate_cost_factor(df, group_by=group_by, filters=filters)
    logger.info(f"Result:\n{result}")
    with open("tests/test_output_component_by_hub.json") as f:
        output = json.load(f)
    assert len(result) == len(output), (
        "Result length does not match expected output length"
    )
    for i in range(len(result)):
        logger.info(f"Comparing row {i}: {result.iloc[i].to_dict()} with {output[i]}")
        assert result.iloc[i].to_dict() == output[i], (
            f"Row {i} does not match expected output"
        )
