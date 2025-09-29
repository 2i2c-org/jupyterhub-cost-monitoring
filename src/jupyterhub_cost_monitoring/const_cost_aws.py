"""
Constants used to compose queries against AWS Cost Explorer API.
"""

import os

# Environment variables based config isn't great, see fixme comment in
# values.yaml under the software configuration heading
CLUSTER_NAME = os.environ["CLUSTER_NAME"]

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

# Metrics:
#
#   UnblendedCost represents costs for an individual AWS account. It is
#   the default metric in the AWS web console. BlendedCosts represents
#   the potentially reduced costs stemming from having multiple AWS
#   accounts in an organization the collectively could enter better
#   pricing tiers.
#
METRICS_UNBLENDED_COST = "UnblendedCost"

# Granularity:
#
#   HOURLY granularity is only available for the last two days, while
#   DAILY is available for the last 13 months.
#
GRANULARITY_DAILY = "DAILY"

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
FILTER_ATTRIBUTABLE_COSTS = {
    # ref: https://github.com/2i2c-org/infrastructure/issues/4787#issue-2519110356
    "Or": [
        {
            "Tags": {
                "Key": "alpha.eksctl.io/cluster-name",
                "Values": [CLUSTER_NAME],
                "MatchOptions": ["EQUALS"],
            },
        },
        {
            "Tags": {
                "Key": f"kubernetes.io/cluster/{CLUSTER_NAME}",
                "Values": ["owned"],
                "MatchOptions": ["EQUALS"],
            },
        },
        {
            "Tags": {
                "Key": "2i2c.org/cluster-name",
                "Values": [CLUSTER_NAME],
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

GROUP_BY_HUB_TAG = {
    "Type": "TAG",
    "Key": "2i2c:hub-name",
}

GROUP_BY_SERVICE_DIMENSION = {
    "Type": "DIMENSION",
    "Key": "SERVICE",
}

FILTER_HOME_STORAGE_COSTS = {
    "Tags": {
        "Key": "2i2c:volume-purpose",
        "Values": ["home-nfs"],
        "MatchOptions": ["EQUALS"],
    }
}


# Some costs like costs associated with core nodes, hub database storage, and support components
# (Prometheus, Grafana, Alertmanager) are not tied to any specific hub or user.
# We consider these core costs and filter them out from compute costs before calculating user costs.
FILTER_CORE_COSTS = {
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
}
