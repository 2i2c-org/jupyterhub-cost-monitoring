import json
from typing import Literal

import numpy as np
import pandas as pd


def generate_test_usage_data(
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
    for date in pd.date_range(from_date, to_date):
        for hub in hubs:
            for component in components:
                entry = {
                    "date": date.strftime("%Y-%m-%d"),
                    "hub": hub,
                    "component": component,
                    "value": np.round(np.random.rand() * factor, 0),
                }
                if len(users) != 0:
                    for user in users:
                        entry.update({"user": user})
                        data.append(entry)
                else:
                    data.append(entry)
    with open(f"test_data_{data_type}.json", "w") as f:
        json.dump(data, f, indent=4)
