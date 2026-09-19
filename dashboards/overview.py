from typing import TypedDict

from grafana_foundation_sdk.builders import common as common_builder
from grafana_foundation_sdk.builders import timeseries
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
    Panel,
    VariableRefresh,
)
from grafana_foundation_sdk.models.resource import DashboardKind, Manifest, Metadata
from infinity import (
    Column,
    ColumnFormat,
    InfinityQueryBuilder,
    QueryFormat,
)


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


def totals() -> Builder[Panel]:
    return make_total_panel(
        "Total Costs",
        [
            {
                "url": "/totals/account?from=${__from:date}&to=${__to:date}",
                "columns": [
                    {
                        "selector": "date",
                        "text": "Date",
                        "type": ColumnFormat.TIMESTAMP,
                    },
                    {
                        "selector": "cost",
                        "text": "Cost of whole account",
                        "type": ColumnFormat.NUMBER,
                    },
                ],
            },
            {
                "url": "/totals/attributable?from=${__from:date}&to=${__to:date}",
                "columns": [
                    {
                        "selector": "date",
                        "text": "Date",
                        "type": ColumnFormat.TIMESTAMP,
                    },
                    {
                        "selector": "cost",
                        "text": "Cost attributable to JupyterHub",
                        "type": ColumnFormat.NUMBER,
                    },
                ],
            },
        ],
    )


def per_hub_per_component():
    return make_total_panel(
        "Cost by component for ${hub}",
        [
            {
                "url": "/hub/by-component?from=${__from:date}&to=${__to:date}&hub=${hub}",
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


def build_dashboard() -> Dashboard:
    builder = (
        Dashboard("Cloud Costs Overview")
        .uid("jupyterhub-cost-monitoring/overview")
        .tags(["generated", "raspberrypi-node-integration"])
        .refresh("1m")
        .time("now-30d", "now-1d")
        .with_variable(
            QueryVariable("hub")
            .label("hub")
            .datasource(DataSourceRef("yesoreyeram-infinity-datasource"))
            .query(
                {
                    # FIXME: This isn't strongly typed, but that's ok for now?
                    "infinityQuery": {
                        "format": "table",
                        "parser": "backend",
                        "source": "url",
                        "type": "json",
                        "url": "/hub/names?from=${__from:date}&to=${__to:date}",
                        # "url": "/hub/names",
                        "url_options": {
                            "method": "GET",
                        },
                    }
                }
            )
            .include_all(True)
            .allow_custom_value(False)
            .multi(True)
            # .current(VariableOption(selected=True))
            # .hide(VariableHide.HIDE_VARIABLE)
            .refresh(VariableRefresh.ON_TIME_RANGE_CHANGED)
        )
        # Set UTC timezone by default, because that's what our prometheus does
        .timezone(TimeZoneUtc)
        .with_row(Row("Overview"))
        .with_panel(totals())
        .with_panel(components())
        .with_panel(hubs())
        .with_row(Row("User Costs Per Hub"))
        .with_panel(per_hub_per_component().repeat("hub").max_per_row(2))
        .preload(True)
    )

    return builder


if __name__ == "__main__":
    dashboard = build_dashboard().build()
    encoder = JSONEncoder(sort_keys=True, indent=2)
    m = Manifest(
        "dashboard.grafana.app/v1",
        kind=DashboardKind,
        metadata=Metadata(name="cloud-cost-overview"),
        spec=dashboard,
    )

    print(encoder.encode(m))
