# Contributing

Please refer to [Project Jupyter's Code of Conduct](https://github.com/jupyter/governance/blob/HEAD/conduct/code_of_conduct.md) for guidelines on fostering a friendly and collaborative environment.

## Setting up a local development environment

This project uses the Python package manager `uv`. Below are the steps to set up a local development environment.

1. Clone this repository

  ```bash
  git clone https://github.com/2i2c-org/jupyterhub-cost-monitoring.git
  ```

1. Install `uv`

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

1. Install project dependencies and source the `.venv` environment

   ```bash
   uv sync
   source .venv/bin/activate
   ```

1. Authenticate with [AWS credentials](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) (requires [AWS CLI installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)). This example uses a [session token](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) from an MFA code associated with an MFA device:

  ```bash
  export AWS_PROFILE=<aws-profile-name>
  export CLUSTER_NAME=<cluster-name>
  export MFA_DEVICE_ID=<mfa-device-id>
  aws sts get-session-token --serial-number $MFA_DEVICE_ID --profile $AWS_PROFILE --token-code ******
  ```

1. Run the Flask web server

   ```bash
   cd src/jupyterhub_cost_monitoring
   flask run --port=8080 --reload
   ```

1. Visit [http://127.0.0.1:8080](http://127.0.0.1:8080) to view the application.

If you need to add or update dependencies, follow the guidance in [Working on projects | uv](https://docs.astral.sh/uv/guides/projects/#managing-dependencies)

## Pre-commit

This project uses [pre-commit](https://pre-commit.com/) to manage pre-commit hooks. To install the pre-commit hooks, run:

```bash
pre-commit install
```

This will set up the hooks defined in `.pre-commit-config.yaml` to run automatically on `git commit`.

## Chartpress

Helm charts are automatically published with [Chartpress](https://github.com/jupyterhub/chartpress) and hosted at [2i2c.org/jupyterhub-cost-monitoring](https://2i2c.org/jupyterhub-cost-monitoring/).

Images are hosted at [Quay.io](https://quay.io/repository/2i2c/jupyterhub-cost-monitoring).

See the configuration in the [`chartpress.yaml`](https://github.com/2i2c-org/jupyterhub-cost-monitoring/blob/main/chartpress.yaml) file for more details.

## Running tests

To run tests, use `pytest`:

```bash
uv run pytest
```
