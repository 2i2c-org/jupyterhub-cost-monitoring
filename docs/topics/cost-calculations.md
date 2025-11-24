# Cost calculations

## User costs

User-level costs are calculated based on the usage of cloud resources by each user. The following resources are considered:

- memory (RAM) requested by user servers
- home directory storage

### `/total-usage`

The `/total-usage` endpoint provides the cost factor of each component by each user, hub, and component. The cost factor is a decimal fraction representing the proportion of the total usage of that component across all users.

The usage for each component is queried from Prometheus as follows:

- **Compute**: The memory (RAM) requested by a user's server is calculated by summing the memory requests of all pods associated with that user. This is done using the following PromQL query:

  ```sql
    sum(kube_pod_container_resource_requests{resource="memory"})
  ```

- **Home directory storage**: The total storage used by a user's home directory is calculated by summing the storage usage over each user folder from the [prometheus-dirsize-exporter](https://github.com/yuvipanda/prometheus-dirsize-exporter). This is done using the following PromQL query:

  ```sql
    sum(dirsize_total_size_bytes)
  ```

Cost factors are calculated as a decimal fraction of the total usage of that resource across all users. For example, if a user has requested 4GiB of memory and the total memory requested by all users is 100GiB, then the cost factor for that user for memory is 0.04.

### `/costs-per-user`

The cost factor from `/total-usage` is then multiplied by the total cost of that component to determine the user cost.

For example, if the total cost of compute for a given day is \$100 and a user has a cost factor of 0.04 for the compute component, then the cost attributed to that user for memory is $4.

### User cost caveats

The proportional usage described above does not take into account the underutilization of a resource. For example

- if a user requests 4GiB of memory for their server but only uses 1GiB, the cost calculation will still attribute costs based on the requested 4GiB
- if a user has a home directory with 10GiB of data out of a total 20GiB used for home directories, but the total disk size provisioned is 100GiB, the cost calculation will still attribute 10/20GiB = 50% of the total home storage costs to that user.

## Group costs

Group-level costs are calculated by aggregating the user-level costs for all users within a group. Each entry in the [`/costs-per-user`](#id-costs-per-user) endpoint includes a `usergroup` key that indicates the group which the user belongs.

:::{note}
Only user group memberships from the most recent dates are considered. Historical user group memberships incur a heavy performance penalty.
:::

There are a few extra endpoints provided by the cost monitoring application to help track user group costs.

### `/total-costs-per-group`

This endpoint summarizes the total costs for each group by summing the costs of all users who belong to that group.

### `/users-with-multiple-groups`

This lists all users with multiple group memberships. This is useful for identifying users whose costs may be double-counted across multiple groups.

### `/users-with-no-groups`

This lists all users with no group memberships. This is useful for identifying users whose costs are not being attributed to any group.

### Group cost caveats

The cost monitoring application cannot make any assumptions for which group costs are accounted for when a user is a member of multiple groups. Therefore, costs incurred by users who belong to multiple groups are double-counted by default in the group cost calculations.

:::{tip} Example – double counting
If user A belongs to both group X and group Y, then the costs attributed to user A will be included in the total group costs for both group X and group Y.
:::
