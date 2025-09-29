# Grafana dashboards

Grafana dashboard designs are encoded as jsonnet templates, using a library called [Grafonnet](https://grafana.github.io/grafonnet/index.html).

## Deployment

These dashboards are deployed using a Python `deploy.py` script from [jupyterhub/grafana-dashboards](https://github.com/jupyterhub/grafana-dashboards)

Running this command has a pre-requisite that you have jsonnet installed,
specifically the jsonnet binary built using golang called go-jsonnet.

## Rendering templates

To render the jsonnet templates, which is useful during development, you
can:

1. Clone the  [jupyterhub/grafana-dashboards](https://github.com/jupyterhub/grafana-dashboards) repository
2. Change directory to the `grafana-dashboards` cloned repo, and then run:

   ```bash
   jsonnet -J vendor /path/to/jupyterhub-cost-monitoring/dashboards/cloud-cost-aws.jsonnet
   ```
