import pandas as pd

from src.jupyterhub_cost_monitoring.logs import get_logger
from src.jupyterhub_cost_monitoring.query_usage import _calculate_daily_cost_factors

logger = get_logger(__name__)


def test_cost_factor_by_hub(input_data_usage, output_data_hub):
    result = _calculate_daily_cost_factors(
        input_data_usage, hub_name="staging"
    )  # TODO: function call should return specified hub, not all hubs
    df_result = pd.DataFrame(result)
    df_output = pd.DataFrame(output_data_hub)
    # column ordering is important for assertion
    df_output = df_output[["date", "hub", "component", "cost_factor", "user"]]
    df_output = df_output.rename(columns={"cost_factor": "value"})
    logger.debug(f"Result: \n{df_result}")
    logger.debug(f"Output: \n{df_output}")
    assert len(df_result) == len(df_output), (
        "Result length does not match expected output length"
    )
    assert pd.testing.assert_frame_equal(df_result, df_output) is None, (
        "Cost factors do not match expected output"
    )
    df_result = (
        df_result.drop(columns=["user"])
        .groupby(["date", "component", "hub"], as_index=False, observed=True)
        .sum()
    )
    assert df_result["value"].all() == 1.0, (
        "Cost factors do not sum to 1 for each date/component/hub grouping"
    )


def test_cost_factor_by_component(input_data_usage, output_data_component):
    result = _calculate_daily_cost_factors(input_data_usage)
    df_result = pd.DataFrame(result)
    df_result = (
        df_result.groupby(["date", "component", "user"], as_index=False)
        .sum()
        .drop(columns=["hub"])
    )
    df_output = pd.DataFrame(output_data_component)
    # Column ordering is important for assertion
    df_output = df_output[["date", "component", "user", "cost_factor"]]
    df_output = df_output.rename(columns={"cost_factor": "value"})
    logger.debug(f"Result: \n{df_result}")
    logger.debug(f"Output: \n{df_output}")
    assert len(df_result) == len(df_output), (
        "Result length does not match expected output length"
    )
    assert pd.testing.assert_frame_equal(df_result, df_output) is None, (
        "Cost factors do not match expected output"
    )
    df_result = (
        df_result.drop(columns=["user"])
        .groupby(["date", "component"], as_index=False, observed=True)
        .sum()
    )
    assert df_result["value"].all() == 1.0, (
        "Cost factors do not sum to 1 for each date/component grouping"
    )
