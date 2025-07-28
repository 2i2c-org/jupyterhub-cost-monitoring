# jupyterhub-cost-monitoring

Cloud cost monitoring is moving beyond just preventing runaway cost explosions – it’s about empowering JupyterHub administrators with the guardrails they need to run efficient, transparent, and sustainable infrastructures. A cloud cost bill can show a broad view of services and machines provisioned, but how can we provide granular insights into each user and the value they are deriving from the hub on an application level?  

This tool provides a per-user cost reporting system for JupyterHubs running on AWS, enabling hub administrators to monitor and report the costs associated with each user. This approach delivers cloud observability and cost transparency that can be reliably deployed using Kubernetes and integrated with Zero to JupyterHub distributions.

## Features

1. Metric Collection – Prometheus collects resource usage metrics (including CPU, memory, and storage) from individual user pods via standard and custom exporters.
2. Cost Estimation – Usage is correlated with AWS cost data to estimate per-user costs.
3. Visualization – Grafana dashboards display rich, interactive views of usage and cost data, making it easy to monitor trends, identify high-cost workloads, and generate reports for funders and decision-makers.

## Contributing

Contributions to the `jupyterhub-cost-monitoring` project are welcome! Please follow the standard GitHub workflow:

1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request.

Please refer to [`CONTRIUBUTING.md`](CONTRIBUTING.md) for more details.

## License

This project is licensed under the [BSD 3-Clause License](LICENSE).
