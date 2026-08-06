# AWS Tags in Use

This document describes the various AWS tags we use.

## `hub_name_tag`

Resources with this tag are accounted for the hub with the name that is
the value of this tag.

```{note}
Currently, we decide that if a resource does not have this tag but is
still attributable to us, it is marked as "support". We should move away from
this over time, see [this issue](https://github.com/2i2c-org/jupyterhub-cost-monitoring/issues/103)
```
