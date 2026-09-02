# AWS Tags in Use

This document describes the various AWS tags we use. They are all configured
as traitlets on the `AWSCostExplorer` object.

## `attributable_costs_filter`

Since a single AWS account can have multiple sets of infrastructure running
in it, we need a way to identify which set of resources we think of as
'ours' and monitor the costs of. This filter determines

## `hub_name_tag`

Resources with this tag are accounted for the hub with the name that is
the value of this tag.

```{note}
Currently, we decide that if a resource does not have this tag but is
still attributable to us, it is marked as "support". We should move away from
this over time, see [this issue](https://github.com/2i2c-org/jupyterhub-cost-monitoring/issues/103)
```

## `core_costs_filter`


## `home_storage_costs_filter`

Resources with this tag are treated as home storage costs.
