"""
Queries to AWS Cost Explorer to get different kinds of cost data.
"""

import copy
import functools
import os
from pprint import pformat

import boto3
from traitlets import Any, Dict, Instance, Unicode, default
from traitlets.config import LoggingConfigurable

from .cache import ttl_lru_cache
from .const_cost_aws import (
    FILTER_USAGE_COSTS,
    GROUP_BY_SERVICE_DIMENSION,
)
from .date_utils import DateRange
from .prometheus import Prometheus


class AWSCostExplorer(LoggingConfigurable):
    prometheus = Instance(
        klass=Prometheus,
    )

    @default("prometheus")
    def _prometheus_default(self):
        return Prometheus(parent=self)

    aws_client_extra_kwargs = Dict(
        Any(),
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
        default={
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

    attributable_costs_filter = Dict(
        Dict(),
        help="""
        AWS Cost Explorer filter for *all* resources we attribute to JupyterHub infrastructure
        """,
        config=True,
    )

    @default("attributable_costs_filter")
    def _attributable_costs_filter_default(self):
        cluster_name = os.environ.get("CLUSTER_NAME")

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
        Dict(),
        default={
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

    @functools.cache
    def component_for_service(self, service_name: str):
        """
        Return the cost monitoring 'component' for a given AWS service name.

        Return "other" with a warning if we don't currently have a classification
        """
        service_component_map = {
            "AWS Backup": "backup",
            "EC2 - Other": "compute",  # Note: this can include EBS volumes and snapshots used for home storage as well
            "Amazon Elastic Compute Cloud - Compute": "compute",
            "Amazon Elastic Container Service for Kubernetes": "core",
            "Amazon Elastic File System": "home storage",
            "Amazon Elastic Load Balancing": "networking",
            "Amazon Simple Storage Service": "object storage",
            "Amazon Virtual Private Cloud": "networking",
        }
        if service_name in service_component_map:
            return service_component_map[service_name]
        else:
            # only printed once per service name thanks to memoization
            self.log.warning(
                f"Service '{service_name}' not categorized as a component yet"
            )
            return "other"

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

    def query_hub_names(self, date_range: DateRange):
        """
        Query list of hubs discovered via cost explorer in the date range

        Returns list of hub names, with empty/None values converted to "support"
        """
        from_date, to_date = date_range.aws_range

        response = self.aws_ce_client.get_tags(
            TimePeriod={"Start": from_date, "End": to_date}, TagKey=self.hub_name_tag
        )
        # FIXME: Understand why none responses are marked as "support"
        hub_names = [t or "support" for t in response["Tags"]]
        return hub_names

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
                        "name": g["Keys"][0].split("$", maxsplit=1)[1] or "support",
                    }
                    for g in e["Groups"]
                ]
            )

        return processed_response

    def _process_home_storage_costs(
        self, entries_by_date, home_storage_ebs_cost_response
    ):
        """
        Helper function to get home storage costs and deduct this from the compute component costs.
        This is because EBS volumes are included in the EC2 - Other service, which is mapped to the
        compute component by default.

        Args:
            entries_by_date: Dictionary indexed by date containing component entries
            home_storage_ebs_cost_response: AWS Cost Explorer response for home storage EBS costs
        """
        for home_e in home_storage_ebs_cost_response["ResultsByTime"]:
            date = home_e["TimePeriod"]["Start"]

            # Calculate total home storage cost for this date
            home_storage_cost = 0.0
            for g in home_e["Groups"]:
                if g["Keys"][0] == "EC2 - Other":
                    home_storage_cost += float(g["Metrics"]["UnblendedCost"]["Amount"])

            if home_storage_cost > 0:
                date_entries = entries_by_date.get(date, {})

                # Subtract from compute component (EC2 - Other maps to compute)
                compute_entry = date_entries.get("compute")
                if compute_entry:
                    current_compute_cost = float(compute_entry["cost"])
                    new_compute_cost = max(
                        0.0, current_compute_cost - home_storage_cost
                    )
                    compute_entry["cost"] = f"{new_compute_cost:.2f}"
                    self.log.debug(
                        f"Adjusted compute cost for {date}: {current_compute_cost:.2f} -> {new_compute_cost:.2f}"
                    )

                # Add to home storage component
                home_storage_entry = date_entries.get("home storage")
                if home_storage_entry:
                    current_home_storage_cost = float(home_storage_entry["cost"])
                    new_home_storage_cost = (
                        current_home_storage_cost + home_storage_cost
                    )
                    home_storage_entry["cost"] = f"{new_home_storage_cost:.2f}"
                    self.log.debug(
                        f"Updated home storage cost for {date}: {current_home_storage_cost:.2f} -> {new_home_storage_cost:.2f}"
                    )
                else:
                    # Create new home storage entry if it doesn't exist
                    new_entry = {
                        "date": date,
                        "cost": f"{home_storage_cost:.2f}",
                        "component": "home storage",
                    }
                    # Update index
                    if date not in entries_by_date:
                        entries_by_date[date] = {}
                    entries_by_date[date]["home storage"] = new_entry
                    self.log.debug(
                        f"Added new home storage entry for {date}: {home_storage_cost:.2f}"
                    )

    def _add_hub_filter(self, filter_dict: dict, hub_name: str | None = None) -> None:
        """
        Add hub-specific filtering to a given filter dictionary.

        Args:
            filter_dict: The filter dictionary to modify (must have "And" key)
            hub_name: The hub name to filter by. If "support", filters for absent hub tags.
                    If a specific name, filters for that hub. If None, no filter added.
        """
        if hub_name == "support":
            filter_dict["And"].append(
                {
                    "Tags": {
                        "Key": self.hub_name_tag,
                        "MatchOptions": ["ABSENT"],
                    },
                }
            )
        elif hub_name:
            filter_dict["And"].append(
                {
                    "Tags": {
                        "Key": self.hub_name_tag,
                        "Values": [hub_name],
                        "MatchOptions": ["EQUALS"],
                    },
                }
            )

    def _create_base_filter(self) -> dict:
        """
        Create the base filter used for most cost queries.

        Returns:
            Base filter dictionary with usage and attributable cost filters
        """
        return {
            "And": [
                FILTER_USAGE_COSTS,
                self.attributable_costs_filter,
            ]
        }

    def _process_core_costs(self, entries_by_date, core_cost_response):
        """
        Helper function to get core infrastructure costs and deduct this from compute costs.

        This is because core node compute and root volumes, support EBS volumes
        and NAT Gateway (if it exists), are mapped to compute by default under
        the EC2 - Other service.

        Args:
            entries_by_date: Dictionary indexed by date containing component entries
            core_cost_response: AWS Cost Explorer response for core costs
        """
        self.log.debug(
            f"Processing core costs: {pformat(core_cost_response['ResultsByTime'])}"
        )
        for core_e in core_cost_response["ResultsByTime"]:
            date = core_e["TimePeriod"]["Start"]

            # Calculate total core cost for this date
            core_cost = 0.0
            for g in core_e["Groups"]:
                core_cost += float(g["Metrics"]["UnblendedCost"]["Amount"])

            if core_cost > 0:
                date_entries = entries_by_date.get(date, {})

                # Subtract from compute component (EC2 - Other maps to compute)
                compute_entry = date_entries.get("compute")
                if compute_entry:
                    current_compute_cost = float(compute_entry["cost"])
                    new_compute_cost = max(0.0, current_compute_cost - core_cost)
                    compute_entry["cost"] = f"{new_compute_cost:.2f}"
                    self.log.debug(
                        f"Adjusted compute cost for {date} (core cost): {current_compute_cost:.2f} -> {new_compute_cost:.2f}"
                    )

                # Add to core component
                core_entry = date_entries.get("core")
                if core_entry:
                    current_core_cost = float(core_entry["cost"])
                    new_core_cost = current_core_cost + core_cost
                    core_entry["cost"] = f"{new_core_cost:.2f}"
                    self.log.debug(
                        f"Updated core cost for {date}: {current_core_cost:.2f} -> {new_core_cost:.2f}"
                    )
                else:
                    # Create new core entry if it doesn't exist
                    new_entry = {
                        "date": date,
                        "cost": f"{core_cost:.2f}",
                        "component": "core",
                    }
                    # Update index
                    if date not in entries_by_date:
                        entries_by_date[date] = {}
                    entries_by_date[date]["core"] = new_entry
                    self.log.debug(f"Added new core entry for {date}: {core_cost:.2f}")

    @ttl_lru_cache(seconds_to_live=3600)
    def query_total_costs_per_component(
        self,
        date_range: DateRange,
        hub_name: str | None = None,
        component: str | None = None,
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
        # Create base filter and add hub-specific filtering
        base_filter = self._create_base_filter()
        self._add_hub_filter(base_filter, hub_name)

        response = self.query(
            date_range=date_range,
            filter=base_filter,
            group_by=[GROUP_BY_SERVICE_DIMENSION],
        )

        processed_response = []

        self.log.debug(f"Processing response: {pformat(response['ResultsByTime'])}")

        for e in response["ResultsByTime"]:
            # coalesce service costs to component costs
            component_costs = {}
            for g in e["Groups"]:
                service_name = g["Keys"][0]
                component_name = self.component_for_service(service_name)
                cost = float(g["Metrics"]["UnblendedCost"]["Amount"])
                component_costs[component_name] = (
                    component_costs.get(component_name, 0.0) + cost
                )

            # Filter to specific component if requested
            self.log.debug(f"Component costs before filtering: {component_costs}")
            if component:
                component_costs = {
                    k: v for k, v in component_costs.items() if k == component
                }

            processed_response.extend(
                [
                    {
                        "date": e["TimePeriod"]["Start"],
                        "cost": f"{cost:.2f}",
                        "component": component_name,
                    }
                    for component_name, cost in component_costs.items()
                ]
            )

        # Create index for faster lookups by date and component name
        entries_by_date = {}
        for entry in processed_response:
            date = entry["date"]
            if date not in entries_by_date:
                entries_by_date[date] = {}
            entries_by_date[date][entry["component"]] = entry

        self.log.debug(f"Entries by date before deduplication: {entries_by_date}\n\n")

        # EC2 - Other is a service that can include costs for EBS volumes and snapshots
        # By default, these costs are mapped to the compute component, but
        # a part of the costs from EBS volumes and snapshots can be attributed to "home storage" too
        # so we need to query those costs separately and adjust the compute costs

        # Create home storage filter using the same base filter and hub filtering
        home_storage_filter = self._create_base_filter()
        self._add_hub_filter(home_storage_filter, hub_name)
        home_storage_filter["And"].append(self.home_storage_costs_filter)

        home_storage_ebs_cost_response = self.query(
            date_range=date_range,
            filter=home_storage_filter,
            group_by=[GROUP_BY_SERVICE_DIMENSION],
        )

        # Process home storage costs and adjust compute costs accordingly
        self._process_home_storage_costs(
            entries_by_date, home_storage_ebs_cost_response
        )

        self.log.debug(
            f"Entries by date after home storage processing: {entries_by_date}\n\n"
        )

        # Query core costs (core nodes, hub databases, support components)
        # These should be subtracted from compute and added to a "core" component
        core_cost_filter = self._create_base_filter()
        self._add_hub_filter(core_cost_filter, hub_name)
        core_cost_filter["And"].append(self.core_costs_filter)

        core_cost_response = self.query(
            date_range=date_range,
            filter=core_cost_filter,
            group_by=[GROUP_BY_SERVICE_DIMENSION],
        )

        # Process core costs and adjust compute costs accordingly
        self._process_core_costs(entries_by_date, core_cost_response)

        self.log.debug(
            f"Entries by date after core cost processing: {entries_by_date}\n\n"
        )

        # Generate final response from index, sorted by date
        final_response = []
        for date in sorted(entries_by_date.keys()):
            for _, entry in entries_by_date[date].items():
                if component and entry["component"] != component:
                    continue
                final_response.append(entry)

        return final_response

    @ttl_lru_cache(seconds_to_live=3600)
    def query_total_costs_per_user(
        self,
        date_range: DateRange,
        hub: str | None = None,
        component: str | None = None,
        user: str | None = None,
        usergroup: str | None = None,
        limit: int | None = None,
    ):
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
        costs_per_component = self.query_total_costs_per_component(
            date_range, hub, component
        )

        costs_by_date = {}
        for entry in costs_per_component:
            costs_by_date.setdefault(entry["date"], {})[entry["component"]] = float(
                entry["cost"]
            )

        # Get user usage percentages from Prometheus using the same DateRange object
        # This ensures we query the same logical date range for both AWS and Prometheus,
        # accounting for their different date range semantics (exclusive vs inclusive)
        usage_shares = self.prometheus.query_usage(
            date_range,
            hub_name=hub,
            component_name=component,
            user_name=user,
        )
        results = []
        for entry in usage_shares:
            d = entry["date"]
            c = entry["component"]
            usage_share = entry["value"]
            if d in costs_by_date and c in costs_by_date[d]:
                total_cost_for_component = costs_by_date[d][c]
                entry["value"] = round(
                    usage_share * total_cost_for_component, 4
                )  # Adjust usage share to cost
                results.append(entry)
        results = [x for x in results if x["hub"] != "binder"]  # Exclude binder hubs
        user_groups = self.prometheus.query_user_groups(date_range, hub, user)
        seen = set()
        list_groups = []
        # Ensure uniquely keyed entries when double-counting group costs
        for r in results:
            matched = False
            for entry in user_groups:
                if r["hub"] == entry["hub"] and r["user"] == entry["username"]:
                    key = (
                        r["date"],
                        r["hub"],
                        r["user"],
                        r["component"],
                        entry["usergroup"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    if "usergroup" not in r:
                        r["usergroup"] = entry["usergroup"]
                        matched = True
                    else:
                        r_copy = copy.deepcopy(r)
                        r_copy["usergroup"] = entry["usergroup"]
                        list_groups.append(r_copy)
                        matched = True
            if not matched:
                key = (r["date"], r["hub"], r["user"], r["component"], "none")
                if key not in seen:
                    seen.add(key)
                    r["usergroup"] = "none"
        results.extend(list_groups)
        if limit:
            limit = int(limit)
            user_costs = {}
            for entry in results:
                user_costs[entry["user"]] = (
                    user_costs.get(entry["user"], 0) + entry["value"]
                )
            top_users = sorted(user_costs.items(), key=lambda x: -x[1])[:limit]
            top_user_set = {user for user, _ in top_users}
            self.log.debug(f"Top users: {top_users}")
            results = [entry for entry in results if entry["user"] in top_user_set]
        results = self.prometheus._filter_json(
            results, hub=hub, component=component, user=user, usergroup=usergroup
        )
        results.sort(
            key=lambda x: (x["date"], x["hub"], x["component"], -float(x["value"]))
        )
        return results

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
