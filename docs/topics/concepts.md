# Concepts

## An "Account"

An Account refers to a cloud provider's unit of billing - "account" for AWS,
"project" for GCP, etc. It may contain infrastructure that is for a JupyterHub
(that we track) as well as other infrastructure (that we do not track).

## "Attributable" costs

Attributable costs are for cloud components that `jupyterhub-cost-monitoring`
recognizes as used by a JupyterHub or its supporting infrastructure. It is
a subset of the "Account" cost.

The sum of all costs that we track should match the entire 'attributable' cost. We track costs across two axes:

### Axis 1: Hubs

A "hub" represents costs attributable to a JupyterHub that is serving users, including:

1. Base cost of the 'always on' JupyterHub control plane
2. Cost of user servers
3. Cost of home directory storage

Multiple JupyterHubs can exist in a single account.

### "Support"

This is a special 'hub' describing per-cluster infrastructure, such
as prometheus, grafana, etc.

```{note}
We should eventually amortize the cost of this into the various hubs
and just treat it as part of the 'always on' control panel
```

### Users

Each hub has a number of *users*, and the sum of all users' cost should match
the cost of the hub.

### Groups

Each user can also belong to a number of different *groups*. However, since
there can be a lot of overlap in groups, the sum of all groups cost doesn't
mean anything.

```{note}
Users and Groups can be thought of ways to *subset* a single hub
```

## Axis 2: Components

We also split cloud costs across different "components", determining the
*kind* of thing that is costing money.

### Compute

### Home Storage

### Object Storage

## Combining Axes

We should be able to combine and query different axes to be able to answer
different questions. For example, you should be able to ask:

1. "Cost of home directory storage (Axis 2) for Hub A (Axis 1)"
2. "Cost of compute (Axis 2) for users A, B, C in Hub A (Axis 1)"
3. "Cost of everyone in Group X in Hub A (Axis 1)"

