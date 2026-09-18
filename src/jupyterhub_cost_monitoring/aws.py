"""
Queries to AWS Cost Explorer to get different kinds of cost data.
"""

import os
from dataclasses import dataclass
from datetime import date

import boto3
from traitlets import Dict, Instance, Unicode, default
from traitlets.config import LoggingConfigurable

from .cache import ttl_lru_cache
from .date_utils import DateRange
from .prometheus import Component, Prometheus

# AWS CE filter for getting only information about usage, rather than taxes, credits, etc
FILTER_USAGE_COSTS = {
    "Dimensions": {
        "Key": "RECORD_TYPE",
        "Values": ["Usage"],
    },
}

# AWS CE group_by clause for grouping charges by service that used them
GROUP_BY_SERVICE_DIMENSION = {
    "Type": "DIMENSION",
    "Key": "SERVICE",
}


@dataclass
class UserCostItem:
    date: date
    user: str
    hub: str
    component: Component
    value: float


@dataclass
class ComponentCostItem:
    date: date
    component: Component
    value: float


class AWSCostExplorer(LoggingConfigurable):
    prometheus = Instance(
        klass=Prometheus,
    )

    @default("prometheus")
    def _prometheus_default(self):
        return Prometheus(parent=self)

    aws_client_extra_kwargs = Dict(
        help="""
        Extra arguments to be passed to the AWS Client that talks to the Cost Explorer
        """,
        config=True,
    )

    hub_name_tag = Unicode(
        "2i2c:hub-name",
        help="""
        Tag name that associates a cloud resource as belonging to a particular hub
        """,
        config=True,
    )

    home_storage_costs_filter = Dict(
        Dict(),
        default_value={
            "Tags": {
                "Key": "2i2c:volume-purpose",
                "Values": ["home-nfs"],
                "MatchOptions": ["EQUALS"],
            }
        },
        help="""
        AWS Cost Explorer Filter for tagging home directory costs.

        Primarily used for the EBS volume that contains the home directory
        used by all users on a hub.
        """,
        config=True,
    )

    network_costs_filter = Dict(
        default_value={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": [
                    "Amazon Virtual Private Cloud",
                    "Amazon Elastic Load Balancing",
                ],
                "MatchOptions": ["EQUALS"],
            }
        },
        help="""
        AWS Cost Explorer Filter for networking costs
        """,
        config=True,
    )

    object_storage_costs_filter = Dict(
        default_value={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": [
                    "Amazon Simple Storage Service",
                ],
                "MatchOptions": ["EQUALS"],
            }
        },
        help="""
        AWS Cost Explorer Filter for user object storage costs
        """,
        config=True,
    )

    user_compute_costs_filter = Dict(
        default_value={
            "And": [
                {
                    "Tags": {
                        "Key": "2i2c:node-purpose",
                        "Values": ["user", "worker"],
                        "MatchOptions": ["EQUALS"],
                    }
                },
                {
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": [
                            "EC2 - Other",
                            "Amazon Elastic Compute Cloud - Compute",
                        ],
                        "MatchOptions": ["EQUALS"],
                    }
                },
            ]
        },
        help="""
        AWS Cost Explorer Filter for tagging user compute costs.
        """,
        config=True,
    )

    attributable_costs_filter = Dict(
        help="""
        AWS Cost Explorer filter for *all* resources we attribute to JupyterHub infrastructure
        """,
        config=True,
    )

    @default("attributable_costs_filter")
    def _attributable_costs_filter_default(self):
        cluster_name = os.environ.get("CLUSTER_NAME")

        if cluster_name is None:
            # We don't want to rely on this environment variable in the future
            raise ValueError(
                "CLUSTER_NAME env var is not set, and required currently. This will change in the future."
            )

        return {
            # https://github.com/2i2c-org/infrastructure/issues/4787#issue-2519110356
            "Or": [
                {
                    "Tags": {
                        "Key": "alpha.eksctl.io/cluster-name",
                        "Values": [cluster_name],
                        "MatchOptions": ["EQUALS"],
                    },
                },
                {
                    "Tags": {
                        "Key": f"kubernetes.io/cluster/{cluster_name}",
                        "Values": ["owned"],
                        "MatchOptions": ["EQUALS"],
                    },
                },
                {
                    "Tags": {
                        "Key": "2i2c.org/cluster-name",
                        "Values": [cluster_name],
                        "MatchOptions": ["EQUALS"],
                    },
                },
                # FIXME: The inclusion of tags 2i2c:hub-name and 2i2c:node-purpose below
                #        in this filter is a patch to capture openscapes data from 1st
                #        July and up to 24th September 2024, and can be removed once
                #        that date range is considered irrelevant.
                #
                {
                    "Not": {
                        "Tags": {
                            "Key": "2i2c:hub-name",
                            "MatchOptions": ["ABSENT"],
                        },
                    },
                },
                {
                    "Not": {
                        "Tags": {
                            "Key": "2i2c:node-purpose",
                            "MatchOptions": ["ABSENT"],
                        },
                    },
                },
            ]
        }

    core_costs_filter = Dict(
        default_value={
            "Or": [
                # Core node storage
                {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "SERVICE",
                                "Values": ["EC2 - Other"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                        {
                            "Tags": {
                                "Key": "2i2c:node-purpose",
                                "Values": ["core"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                    ]
                },
                # Core node compute
                {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "SERVICE",
                                "Values": ["Amazon Elastic Compute Cloud - Compute"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                        {
                            "Tags": {
                                "Key": "2i2c:node-purpose",
                                "Values": ["core"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                    ]
                },
                # Cluster NAT gateway - common for all hubs
                {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "SERVICE",
                                "Values": ["EC2 - Other"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                        {
                            "Dimensions": {
                                "Key": "USAGE_TYPE_GROUP",
                                "Values": [
                                    "EC2: NAT Gateway - Running Hours",
                                    "EC2: NAT Gateway - Data Processed",
                                ],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                    ]
                },
                # Hub database storage
                {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "SERVICE",
                                "Values": ["EC2 - Other"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                        {
                            "Tags": {
                                "Key": "kubernetes.io/created-for/pvc/name",
                                "Values": ["hub-db-dir"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                    ]
                },
                # Support components storage (Prometheus, Grafana, Alertmanager)
                {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "SERVICE",
                                "Values": ["EC2 - Other"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                        {
                            "Tags": {
                                "Key": "kubernetes.io/created-for/pvc/namespace",
                                "Values": ["support"],
                                "MatchOptions": ["EQUALS"],
                            },
                        },
                    ]
                },
            ]
        },
        help="""
        AWS Cost Explorer filter for resources described as 'core' costs
        """,
        config=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aws_ce_client = boto3.client("ce", **self.aws_client_extra_kwargs)

    def query(self, date_range: DateRange, filter, group_by):
        """
        Function meant to be responsible for making the API call and handling
        pagination etc. Currently pagination isn't handled.
        """
        from_date, to_date = date_range.aws_range

        # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce/client/get_cost_and_usage.html#get-cost-and-usage
        response = self.aws_ce_client.get_cost_and_usage(
            # Consistently use unblended costs everywhere
            Metrics=["UnblendedCost"],
            # Hourly data is only available for last 2 days, while
            # daily data is available for last 13 months. Consistently stick to daily data
            Granularity="DAILY",
            TimePeriod={"Start": from_date, "End": to_date},
            Filter=filter,
            GroupBy=group_by,
        )
        # FIXME: Handle pagination, but until this is a need, error loudly instead
        #        of accounting partial costs only.
        if response.get("NextPageToken"):
            raise ValueError(
                f"A query with from '{from_date}' and to '{to_date}' led to "
                "jupyterhub-cost-monitoring needing to handle a paginated response "
                "and that hasn't been worked yet, it needs to be fixed."
            )

        return response

    @ttl_lru_cache(seconds_to_live=3600)
    def query_hub_names(self, date_range: DateRange):
        """
        Query list of hubs discovered via cost explorer in the date range

        Returns list of hub names, with empty/None values converted to "support"
        """
        from_date, to_date = date_range.aws_range

        response = self.aws_ce_client.get_tags(
            TimePeriod={"Start": from_date, "End": to_date}, TagKey=self.hub_name_tag
        )
        hub_names = [t for t in response["Tags"] if t]
        return hub_names

    @ttl_lru_cache(seconds_to_live=3600)
    def query_account_costs(self, date_range: DateRange):
        response = self.query(
            date_range=date_range,
            filter=FILTER_USAGE_COSTS,
            group_by=[],
        )

        processed_response = [
            {
                "date": e["TimePeriod"]["Start"],
                "cost": f"{float(e['Total']['UnblendedCost']['Amount']):.2f}",
                "name": "account",
            }
            for e in response["ResultsByTime"]
        ]

        return processed_response

    @ttl_lru_cache(seconds_to_live=3600)
    def query_attributable_costs(self, date_range: DateRange):
        response = self.query(
            date_range=date_range,
            filter={
                "And": [
                    FILTER_USAGE_COSTS,
                    self.attributable_costs_filter,
                ]
            },
            group_by=[],
        )

        processed_response = [
            {
                "date": e["TimePeriod"]["Start"],
                "cost": f"{float(e['Total']['UnblendedCost']['Amount']):.2f}",
                "name": "attributable",
            }
            for e in response["ResultsByTime"]
        ]

        return processed_response

    @ttl_lru_cache(seconds_to_live=3600)
    def query_total_costs_per_hub(self, date_range: DateRange):
        """
        Query total costs per hub from AWS Cost Explorer for the given date range.

        Costs not attributed to a specific hub are listed under 'support'.

        Args:
            date_range: DateRange object containing the time period for the query

        Returns:
            List of cost entries with 'date', 'cost', and 'name' (hub name) fields
        """

        response = self.query(
            date_range=date_range,
            filter={
                "And": [
                    FILTER_USAGE_COSTS,
                    self.attributable_costs_filter,
                ]
            },
            group_by=[{"Type": "TAG", "Key": self.hub_name_tag}],
        )

        processed_response = []
        for e in response["ResultsByTime"]:
            processed_response.extend(
                [
                    {
                        "date": e["TimePeriod"]["Start"],
                        "cost": f"{float(g['Metrics']['UnblendedCost']['Amount']):.2f}",
                        "name": g["Keys"][0].split("$", maxsplit=1)[1] or "other",
                    }
                    for g in e["Groups"]
                ]
            )

        return processed_response

    def get_per_day_costs(
        self, date_range: DateRange, ce_filter: list[dict]
    ) -> dict[date, float]:
        full_filter = {
            "And": [FILTER_USAGE_COSTS, self.attributable_costs_filter] + ce_filter
        }
        response = self.query(date_range, full_filter, [])
        costs: dict[date, float] = {}
        for entry in response["ResultsByTime"]:
            costs[date.fromisoformat(entry["TimePeriod"]["Start"])] = float(
                entry["Total"]["UnblendedCost"]["Amount"]
            )

        return costs

    def query_per_hub_costs_per_component(self, date_range: DateRange, hub_name: str):
        hub_filter = {
            "Tags": {
                "Key": self.hub_name_tag,
                "Values": [hub_name],
                "MatchOptions": ["EQUALS"],
            }
        }

        compute_costs = self.get_per_day_costs(
            date_range, [self.user_compute_costs_filter, hub_filter]
        )
        home_storage_costs = self.get_per_day_costs(
            date_range, [self.home_storage_costs_filter, hub_filter]
        )

        return {
            Component.USER_COMPUTE: compute_costs,
            Component.USER_HOME_STORAGE: home_storage_costs,
        }

    def query_total_costs_per_component(
        self, date_range: DateRange, components: list[Component] | None = None
    ):
        """
        Query total costs per component from AWS Cost Explorer for the given date range.

        A component is a logical grouping of AWS services (e.g., compute, storage).

        Args:
            date_range: DateRange object containing the time period for the query
            hub_name: The hub name to filter by. If "support", filters for support costs not tied to any specific hub. If a specific name, filters for that hub. If None, queries all hubs.
            component: The component to filter by. If None, queries all components.

        Returns:
            List of dicts with keys: date, cost, component
        """

        if components is None:
            components = [
                Component.CORE,
                Component.USER_HOME_STORAGE,
                Component.NETWORKING,
                Component.USER_COMPUTE,
                Component.USER_OBJECT_STORAGE,
            ]

        component_filter_map = {
            Component.CORE: self.core_costs_filter,
            Component.USER_HOME_STORAGE: self.home_storage_costs_filter,
            Component.NETWORKING: self.network_costs_filter,
            Component.USER_COMPUTE: self.user_compute_costs_filter,
            Component.USER_OBJECT_STORAGE: self.object_storage_costs_filter,
        }

        return dict(
            [
                (c, self.get_per_day_costs(date_range, [component_filter_map[c]]))
                for c in components
            ]
        )

    @ttl_lru_cache(seconds_to_live=3600)
    def query_total_costs_per_user(
        self,
        date_range: DateRange,
    ) -> list[UserCostItem]:
        """
        Query total costs per user by combining AWS costs with Prometheus usage data.

        This function calculates individual user costs by:
        1. Getting total AWS costs per component (compute, home storage) from Cost Explorer
        2. Getting usage fractions per user from Prometheus metrics
        3. Multiplying total costs by each user's usage fraction

        Excludes hubs with no users (e.g., binder hubs)

        Args:
            date_range: DateRange object containing the time period for the query
            hub: The hub namespace to query (optional, if None queries all hubs)
            component: The component to query (optional, if None queries all components)
            user: The user to query (optional, if None queries all users)
            usergroup: The user group to query (optional, if None queries all user groups)
            limit: Limit number of results to top N users by total cost (optional, if None returns all users)

        Returns:
            List of dicts with keys: date, hub, component, user, value (cost in USD)
            Results are sorted by date, hub, component, then value (highest cost first)
        """
        # Get AWS cost data using the DateRange object
        costs_per_component = self.query_total_costs_per_component(date_range)

        # Get user usage percentages from Prometheus using the same DateRange object
        # This ensures we query the same logical date range for both AWS and Prometheus,
        # accounting for their different date range semantics (exclusive vs inclusive)
        usage = self.prometheus.query_usage(date_range)

        cost_items: list[UserCostItem] = []
        for ts, usage_fractions in usage.items():
            for uf in usage_fractions:
                # FIXME: This should be a general filter elsewhere
                # filter out "binder" items
                if uf.hub == "binder":
                    continue

                # FIXME: I'm not sure what exactly to do here, nor why this is happening
                # Something to do with us shifting dates I'm sure.
                if ts not in costs_per_component[uf.component]:
                    print(f"Missing {ts} in {uf.component}")
                    continue

                cost_items.append(
                    UserCostItem(
                        date=ts,
                        user=uf.username,
                        hub=uf.hub,
                        component=uf.component,
                        # FIXME: We shouldn't round here but in grafana
                        value=round(
                            uf.fraction * costs_per_component[uf.component][ts], 4
                        ),
                    )
                )

        cost_items.sort(key=lambda x: (x.date, x.hub, x.component, -float(x.value)))

        return cost_items

    @ttl_lru_cache(seconds_to_live=3600)
    def query_total_costs_per_group(
        self,
        date_range: DateRange,
    ):
        """
        Query total costs per group for the given date range.

        Args:
            date_range: DateRange object containing the time period for the query.

        Returns:
            List of dicts with keys: date, usergroup and cost.
        """
        results = self.query_total_costs_per_user(date_range=date_range)
        response = {}
        for r in results:
            key = (r["date"], r["usergroup"])
            self.log.debug(f"Key: {key}, Value: {r['value']}")
            response[key] = response.get(key, 0) + float(r["value"])

        final_response = [
            {"date": k[0], "usergroup": k[1], "cost": v} for k, v in response.items()
        ]

        return final_response
