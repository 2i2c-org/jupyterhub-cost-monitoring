import json
from typing import Literal

import numpy as np
import pandas as pd


def generate_test_data(
    data_type: str = Literal["usage", "cost"],
    from_date: str = "2025-01-01",
    to_date: str = "2025-01-02",
    hubs: list[str] = ["staging", "prod"],
    components: list[str] = ["compute", "home-directory"],
    n_users: int | None = 3,
) -> None:
    """
    Generate test data.
    """
    if data_type == "usage":
        users = [f"user_{i}" for i in range(n_users)]
        factor = 1e1
    elif data_type == "cost":
        users = []
        factor = 1e3
    data = []
    if data_type == "usage":
        for date in pd.date_range(from_date, to_date):
            for hub in hubs:
                for component in components:
                    for user in users:
                        entry = {
                            "date": date.strftime("%Y-%m-%d"),
                            "hub": hub,
                            "component": component,
                            "value": np.round(np.random.rand() * factor, 0),
                            "user": user,
                        }
                        data.append(entry)
    else:
        for date in pd.date_range(from_date, to_date):
            for hub in hubs:
                for component in components:
                    entry = {
                        "date": date.strftime("%Y-%m-%d"),
                        "hub": hub,
                        "component": component,
                        "value": np.round(np.random.rand() * factor, 0),
                    }
    with open(f"test_data_{data_type}.json", "w") as f:
        json.dump(data, f, indent=4)


def generate_test_output_hub():
    """
    Generate test output grouped by hub based on the test usage and test cost data.
    """
    with open("test_data_usage.json") as f:
        data_usage = json.load(f)
    with open("test_data_cost.json") as f:
        data_cost = json.load(f)
    df_usage = pd.DataFrame(data_usage)
    df_cost = pd.DataFrame(data_cost)
    total_usage = df_usage.groupby(["date", "component", "hub"])["value"].transform(
        "sum"
    )
    df_usage["cost_factor"] = df_usage["value"] / total_usage
    merged = df_usage.merge(df_cost, on=["date", "component", "hub"], how="left")
    merged["cost"] = merged["cost_factor"] * merged["value_y"]
    df_usage["cost"] = merged["cost"]
    df_usage.to_json("test_output_hub.json", orient="records", indent=4)


def generate_test_output_component():
    """
    Generate test output grouped by component based on the test usage and test cost data.
    """
    with open("test_data_usage.json") as f:
        data_usage = json.load(f)
    with open("test_data_cost.json") as f:
        data_cost = json.load(f)
    df_usage = pd.DataFrame(data_usage)
    df_usage = df_usage.groupby(["date", "component", "user"], as_index=False).sum()
    df_cost = pd.DataFrame(data_cost)
    df_cost = (
        df_cost.groupby(["date", "component"], as_index=False)
        .sum()
        .drop(columns=["hub"])
    )
    total_usage = df_usage.groupby(["date", "component"], as_index=False)[
        "value"
    ].transform("sum")
    df_usage["cost_factor"] = (
        df_usage.groupby(["date", "component", "user"], as_index=False)[
            "value"
        ].transform("sum")
        / total_usage
    )
    merged = df_usage.merge(df_cost, on=["date", "component"], how="left")
    merged["cost"] = merged["cost_factor"] * merged["value_y"]
    df_usage["cost"] = merged["cost"]
    df_usage = df_usage.drop(columns=["hub"])
    df_usage.to_json("test_output_component.json", orient="records", indent=4)
