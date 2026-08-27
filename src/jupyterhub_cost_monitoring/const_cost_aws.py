"""
Constants used to compose queries against AWS Cost Explorer API.
"""

import os

# Environment variables based config isn't great, see fixme comment in
# values.yaml under the software configuration heading
CLUSTER_NAME = os.environ.get("CLUSTER_NAME", "")
if not CLUSTER_NAME:
    raise ValueError("$CLUSTER_NAME is not set")

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
