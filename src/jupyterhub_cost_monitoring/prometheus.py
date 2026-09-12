"""
Query the Prometheus server to get usage of JupyterHub resources.
"""

import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Dict, Tuple

import escapism
import requests
from traitlets import Integer, Unicode
from traitlets.config import LoggingConfigurable
from yarl import URL

from .cache import ttl_lru_cache
from .date_utils import DateRange, get_now_date

#
MEMORY_USAGE_FRACTION = """
    sum_over_time(
        sum(
            kube_pod_container_resource_requests{resource="memory"} * on (namespace, pod)
                group_left(annotation_hub_jupyter_org_username)
                group(
                    kube_pod_annotations{annotation_hub_jupyter_org_username!=""}
                ) by (pod, namespace, annotation_hub_jupyter_org_username)
        ) by (annotation_hub_jupyter_org_username, namespace)
        [1d:1m]
    )

     / ignoring(annotation_hub_jupyter_org_username) group_left(namespace)

     sum_over_time(
         sum(
             kube_pod_container_resource_requests{resource="memory"} * on (namespace, pod)
                 group_left(annotation_hub_jupyter_org_username)
                 group(
                     kube_pod_annotations{annotation_hub_jupyter_org_username!=""}
                 ) by (pod, namespace, annotation_hub_jupyter_org_username)
         ) by (namespace)
         [1d:1m]
     )
"""


class Component(Enum):
    """
    Components that we split all costs into
    """

    USER_COMPUTE = "user_compute"
    """Compute costs from infrastructure spawned for user pods"""

    CORE = "core"
    """Compute costs for 'always on' core infrastructure"""

    USER_HOME_STORAGE = "home_storage"
    """Costs for home directory storage"""

    USER_OBJECT_STORAGE = "object_storage"
    """Costs for object storage"""

    NETWORKING = "networking"
    """Costs for network related actions (ingress, egress, etc)"""


MEMORY_REQUESTS_PER_USER = """
    label_replace(
        sum(
        kube_pod_container_resource_requests{resource="memory"} * on (namespace, pod)
        group_left(annotation_hub_jupyter_org_username) group(
            kube_pod_annotations{annotation_hub_jupyter_org_username!=""}
            ) by (pod, namespace, annotation_hub_jupyter_org_username)
        ) by (annotation_hub_jupyter_org_username, namespace),
        "username", "$1", "annotation_hub_jupyter_org_username", "(.*)"
    )
"""

STORAGE_USER_FRACTION = """
    sum(dirsize_total_size_bytes{namespace!=""}) by (namespace, directory)
    / ignoring(directory) group_left(namespace)
    sum(dirsize_total_size_bytes{namespace!=""}) by (namespace)
"""

USER_GROUP_INFO = """
    group(jupyterhub_user_group_info) by (namespace, username, username_escaped, usergroup)
    """


@dataclass(frozen=True)
class User:
    hub: str
    name: str
    escaped_name: str
    groups: set[str]

    def flatten(self):
        """
        Return a flat list, with one entry per group this user is in
        """
        return [
            {
                "hub": self.hub,
                "username": self.name,
                "username_escaped": self.escaped_name,
                "usergroup": group,
            }
            # Sort so we always get consistent ordering in our outputs
            for group in sorted(self.groups)
        ]


@dataclass(frozen=True)
class UsageFraction:
    username: str
    hub: str
    component: Component
    fraction: float


class Prometheus(LoggingConfigurable):
    host = Unicode(
        os.environ.get("SUPPORT_PROMETHEUS_SERVER_SERVICE_HOST", "localhost"),
        help="Host where the prometheus server is running",
        config=True,
    )
    port = Integer(
        int(os.environ.get("SUPPORT_PROMETHEUS_SERVER_SERVICE_PORT", 9090)),
        help="Port where the prometheus server is running",
        config=True,
    )

    username = Unicode(
        os.environ.get("PROMETHEUS_USERNAME", None),
        allow_none=True,
        help="HTTP Basic Auth username required to talk to prometheus (if required)",
        config=True,
    )

    password = Unicode(
        os.environ.get("PROMETHEUS_PASSWORD", None),
        allow_none=True,
        help="HTTP Basic Auth password required to talk to prometheus (if required)",
        config=True,
    )

    def query(self, query: str, date_range: DateRange, step: str):
        """
        Query the Prometheus server with the given query over a date range.

        Args:
            query: The Prometheus query string
            date_range: DateRange object containing the time period for the query
            step: The query resolution step duration

        Returns:
            JSON response from Prometheus API
        """
        # Use Prometheus-formatted dates (inclusive date range with ISO timestamps)
        from_date, to_date = date_range.prometheus_range

        prometheus_api = URL.build(scheme="http", host=self.host, port=self.port)
        if self.username is not None and self.password is not None:
            prometheus_auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        else:
            prometheus_auth = None
        parameters = {
            "query": query,
            "start": from_date,
            "end": to_date,
            "step": step,
        }
        query_api = URL(prometheus_api.with_path("/api/v1/query_range"))
        with requests.get(
            query_api, params=parameters, auth=prometheus_auth
        ) as response:
            self.log.info(f"Querying Prometheus: {response.url}")
            response.raise_for_status()
            result = response.json()
            return result

    @ttl_lru_cache(seconds_to_live=3600)
    def query_usage(
        self,
        date_range: DateRange,
        hub_name: str | None = None,
        components: list[Component] | None = None,
        user_name: str | None = None,
    ) -> Dict[date, list[UsageFraction]]:
        """
        Query usage cost factors per user from the Prometheus server.

        Returns daily usage cost factors (0-1) for each user, where cost factors represent
        each user's share of total resource usage and sum to 1 across all users
        within each date/hub/component combination.

        Args:
            date_range: DateRange object containing the time period for the query
            hub_name: Optional name of the hub to filter results.
            component_name: Optional name of the component to filter results.
            user_name: Optional name of the user to filter results.
        """
        if components is None:
            components = [Component.USER_COMPUTE, Component.USER_HOME_STORAGE]

        # FIXME: implement hub_name filtering
        # FIXME: implement user_name filtering

        usage_fractions: Dict[date, list[UsageFraction]] = {}

        if Component.USER_COMPUTE in components:
            usage_response = self.query(MEMORY_USAGE_FRACTION, date_range, "1d")

            for entry in usage_response["data"]["result"]:
                username = entry["metric"]["annotation_hub_jupyter_org_username"]
                hub = entry["metric"]["namespace"]
                for value in entry["values"]:
                    ts = date.fromtimestamp(value[0])
                    uf = UsageFraction(
                        username=username,
                        hub=hub,
                        component=Component.USER_COMPUTE,
                        fraction=float(value[1]),
                    )
                    usage_fractions.setdefault(ts, []).append(uf)

        if Component.USER_HOME_STORAGE in components:
            usage_response = self.query(STORAGE_USER_FRACTION, date_range, "1d")

            for entry in usage_response["data"]["result"]:
                username = escapism.unescape(
                    entry["metric"]["directory"], escape_char="-"
                )
                hub = entry["metric"]["namespace"]
                for value in entry["values"]:
                    ts = date.fromtimestamp(value[0])
                    uf = UsageFraction(
                        username=username,
                        hub=hub,
                        component=Component.USER_HOME_STORAGE,
                        fraction=float(value[1]),
                    )
                    usage_fractions.setdefault(ts, []).append(uf)

        return usage_fractions

    @ttl_lru_cache(seconds_to_live=3600)
    def query_user_groups(
        self,
        date_range: DateRange,
        hub_name: str | None = None,
        user_name: str | None = None,
        group_name: str | None = None,
    ) -> list[User]:
        """
        Get user group information from the Prometheus server for the most recent day.
        """
        # FIXME: We are ignoring the passed in `date_range` to preserve
        # older behavior of how groups are determined. This should be
        # changed in the future
        now_date = get_now_date() - timedelta(days=1)
        date_range = DateRange(start_date=now_date, end_date=now_date)
        response = self.query(USER_GROUP_INFO, date_range, step="1d")
        with open("1-raw.json", "w") as f:
            json.dump(response, f)

        users: Dict[Tuple[str, str], User] = {}
        for data in response["data"]["result"]:
            hub = data["metric"]["namespace"]
            username = data["metric"]["username"]
            user_escaped = data["metric"]["username_escaped"]
            group = data["metric"]["usergroup"]
            key = (hub, username)
            if key in users:
                user = users[key]
                user.groups.add(group)
            else:
                users[key] = User(hub, username, user_escaped, set([group]))

        return list(users.values())
