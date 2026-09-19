from typing import TypedDict

from grafana_foundation_sdk.builders import common as common_builder
from grafana_foundation_sdk.builders import stat, table, timeseries
from grafana_foundation_sdk.builders.dashboard import (
    Dashboard,
    QueryVariable,
    Row,
)
from grafana_foundation_sdk.cog.builder import Builder
from grafana_foundation_sdk.cog.encoder import JSONEncoder
from grafana_foundation_sdk.models import common, units
from grafana_foundation_sdk.models.common import (
    DataSourceRef,
    TimeZoneUtc,
)
from grafana_foundation_sdk.models.dashboard import (
    DataTransformerConfig,
    Panel,
    VariableOption,
    VariableRefresh,
)
from grafana_foundation_sdk.models.resource import DashboardKind, Manifest, Metadata
from infinity import (
    Column,
    ColumnFormat,
    InfinityQueryBuilder,
    QueryFormat,
)
from overview import per_hub_per_component


class UrlQueryEntries(TypedDict):
    url: str
    columns: list[Column]


def make_total_panel(title: str, url_queries: list[UrlQueryEntries]):
    p = (
        timeseries.Panel()
        .title(title)
        .unit(units.Dollars)
        .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
        .legend(
            common_builder.VizLegendOptions()
            .display_mode(common.LegendDisplayMode.TABLE)
            .placement(common.LegendPlacement.BOTTOM)
            .calcs(["min", "max", "median", "sum"])
            .show_legend(True)
        )
        .span(24)
    )
    for uq in url_queries:
        p = p.with_target(
            InfinityQueryBuilder()
            .with_format(QueryFormat.TIMESERIES)
            .with_url(uq["url"], method="GET")
            .with_columns(uq["columns"])
        )
    return p


def hubs() -> Builder[Panel]:
    return make_total_panel(
        "Cost by Hub",
        [
            {
                "url": "/totals/by-hub?from=${__from:date}&to=${__to:date}",
                "columns": [
                    {
                        "selector": "date",
                        "text": "Date",
                        "type": ColumnFormat.TIMESTAMP,
                    },
                    {"selector": "name", "text": "Hub", "type": ColumnFormat.STRING},
                    {
                        "selector": "cost",
                        "text": "Cost",
                        "type": ColumnFormat.NUMBER,
                    },
                ],
            }
        ],
    )


def components() -> Builder[Panel]:
    return make_total_panel(
        "Cost by Component",
        [
            {
                "url": "/totals/by-component?from=${__from:date}&to=${__to:date}",
                "columns": [
                    {
                        "selector": "date",
                        "text": "Date",
                        "type": ColumnFormat.TIMESTAMP,
                    },
                    {
                        "selector": "component",
                        "text": "Component",
                        "type": ColumnFormat.STRING,
                    },
                    {
                        "selector": "cost",
                        "text": "Cost",
                        "type": ColumnFormat.NUMBER,
                    },
                ],
            }
        ],
    )


def user_table():
    return (
        table.Panel()
        .title("User Cloud Costs")
        .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
        .span(24)
        .height(16)
        .with_target(
            InfinityQueryBuilder()
            .with_format(QueryFormat.TABLE)
            .with_url(
                "/totals/by-user?from=${__from:date}&to=${__to:date}&hub=${hub}", "GET"
            )
            .with_columns(
                [
                    {
                        "selector": "date",
                        "type": ColumnFormat.TIMESTAMP,
                        "text": "Date",
                    },
                    {
                        "selector": "component_costs.compute",
                        "type": ColumnFormat.NUMBER,
                        "text": "Compute Cost",
                    },
                    {
                        "selector": "component_costs.home_storage",
                        "type": ColumnFormat.NUMBER,
                        "text": "Home Directory Cost",
                    },
                    {
                        "selector": "total_cost",
                        "type": ColumnFormat.NUMBER,
                        "text": "Total Cost",
                    },
                    {
                        "selector": "username",
                        "type": ColumnFormat.STRING,
                        "text": "User Name",
                    },
                ]
            )
        )
        .filterable(True)
        .with_transformation(
            DataTransformerConfig(
                "groupBy",
                options={
                    "fields": {
                        "Total Cost": {
                            "aggregations": ["sum"],
                            "operation": "aggregate",
                        },
                        "Compute Cost": {
                            "aggregations": ["sum"],
                            "operation": "aggregate",
                        },
                        "Home Directory Cost": {
                            "aggregations": ["sum"],
                            "operation": "aggregate",
                        },
                        "User Name": {"aggregations": [], "operation": "groupby"},
                    }
                },
            )
        )
        .footer(
            common_builder.TableFooterOptions()
            # FIXME: doesn't seem to work?
            .reducer(["max", "mean", "median"])
        )
    )


def component_stat(title: str, component: str):
    return (
        stat.Panel()
        .title(title)
        .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
        .span(8)
        .unit(units.Dollars)
        .with_target(
            InfinityQueryBuilder()
            .with_format(QueryFormat.TABLE)
            .with_url(
                "/hub/by-component?from=${__from:date}&to=${__to:date}&hub=${hub}&component=%s"
                % component,
                "GET",
            )
            .with_columns(
                [
                    {
                        "selector": "date",
                        "type": ColumnFormat.TIMESTAMP,
                        "text": "Date",
                    },
                    {"selector": "cost", "type": ColumnFormat.NUMBER, "text": "Cost"},
                ]
            )
        )
        .reduce_options(common_builder.ReduceDataOptions().calcs(["sum"]))
    )


def totals() -> Builder[Panel]:
    return (
        stat.Panel()
        .title("Total Cost")
        .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
        .span(8)
        .unit(units.Dollars)
        .with_target(
            InfinityQueryBuilder()
            .with_format(QueryFormat.TABLE)
            .with_url(
                "/totals/by-hub?from=${__from:date}&to=${__to:date}&hub=${hub}", "GET"
            )
            .with_columns(
                [
                    {
                        "selector": "date",
                        "type": ColumnFormat.TIMESTAMP,
                        "text": "Date",
                    },
                    {"selector": "cost", "type": ColumnFormat.NUMBER, "text": "Cost"},
                ]
            )
        )
        .reduce_options(common_builder.ReduceDataOptions().calcs(["sum"]))
    )


def build_dashboard() -> Dashboard:
    builder = (
        Dashboard("Hub Cloud Costs")
        .uid("jupyterhub-cost-monitoring/hub")
        .refresh("1m")
        .time("now-30d", "now-1d")
        .with_variable(
            QueryVariable("hub")
            .label("hub")
            .static_options(
                [
                    VariableOption(value="prod", text="prod", selected=True),
                    VariableOption(value="staging", text="staging"),
                    VariableOption(value="binder", text="staging"),
                ]
            )
            # .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
            # .query(
            #     {
            #         # FIXME: This isn't strongly typed, but that's ok for now?
            #         "infinityQuery": {
            #             "format": "table",
            #             "parser": "backend",
            #             "source": "url",
            #             "type": "json",
            #             "url": "/hub/names?from=${__from:date}&to=${__to:date}",
            #             # "url": "/hub/names",
            #             "url_options": {
            #                 "method": "GET",
            #             },
            #         }
            #     }
            # )
            .include_all(False)
            .allow_custom_value(False)
            .multi(False)
            # .current(VariableOption(selected=True))
            # .hide(VariableHide.HIDE_VARIABLE)
            .refresh(VariableRefresh.ON_TIME_RANGE_CHANGED)
        )
        # Set UTC timezone by default, because that's what our prometheus does
        .timezone(TimeZoneUtc)
        .with_row(Row("Overview for hub ${hub}"))
        .with_panel(totals())
        .with_panel(per_hub_per_component().span(16))
        .with_row(Row("User Details"))
        .with_panel(user_table())
        .preload(True)
    )

    return builder


if __name__ == "__main__":
    dashboard = build_dashboard().build()
    encoder = JSONEncoder(sort_keys=True, indent=2)
    m = Manifest(
        "dashboard.grafana.app/v1",
        kind=DashboardKind,
        metadata=Metadata(name="cloud-cost-hub"),
        spec=dashboard,
    )

    print(encoder.encode(m))
