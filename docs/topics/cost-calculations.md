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
