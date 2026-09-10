# Grafana dashboards

Grafana dashboard designs are encoded as jsonnet templates, using a library called [Grafonnet](https://grafana.github.io/grafonnet/index.html).

## Jsonnet library

We use [jsonnet-bundler](https://github.com/jsonnet-bundler/jsonnet-bundler/)
to manage our dependencies, just like [jupyterhub/grafana-dashboards](https://github.com/jupyterhub/grafana-dashboards/)

1. Install [jsonnet-bundler](github.com/jupyterhub/grafana-dashboards/)

2. In the `dashboards` directory, run `jb install`

## Rendering templates

To render the jsonnet templates, which is useful during development, you
can:

1. In the `dashboards` directory, run:

  ```bash
  jsonnet -J vendor <jsonnet-file>
  ```

2. You can paste the rendered JSON directly into the 'import dashboard' screen on a grafana to test it out