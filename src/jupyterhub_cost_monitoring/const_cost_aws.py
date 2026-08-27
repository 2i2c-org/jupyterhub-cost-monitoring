"""
Constants used to compose queries against AWS Cost Explorer API.
"""

import os

# Environment variables based config isn't great, see fixme comment in
# values.yaml under the software configuration heading
CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "")
if not CLUSTER_NAME:
    raise ValueError("$CLUSTER_NAME is not set")

SERVICE_COMPONENT_MAP = {
    "AWS Backup": "backup",
    "EC2 - Other": "compute",  # Note: this can include EBS volumes and snapshots used for home storage as well
    "Amazon Elastic Compute Cloud - Compute": "compute",
    "Amazon Elastic Container Service for Kubernetes": "core",
    "Amazon Elastic File System": "home storage",
    "Amazon Elastic Load Balancing": "networking",
    "Amazon Simple Storage Service": "object storage",
    "Amazon Virtual Private Cloud": "networking",
}

# Filter:
#
# The various filter objects are meant to be combined based on the needs for
# different kinds of queries.
#
FILTER_USAGE_COSTS = {
    "Dimensions": {
        # RECORD_TYPE is also called Charge type. By filtering on this
        # we avoid results related to credits, tax, etc.
        "Key": "RECORD_TYPE",
        "Values": ["Usage"],
    },
}

GROUP_BY_SERVICE_DIMENSION = {
    "Type": "DIMENSION",
    "Key": "SERVICE",
}


# Some costs like costs associated with core nodes, hub database storage, and support components
# (Prometheus, Grafana, Alertmanager) are not tied to any specific hub or user.
# We consider these core costs and filter them out from compute costs before calculating user costs.
