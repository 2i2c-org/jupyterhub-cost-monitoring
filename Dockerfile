FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y tini git

COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /uvx /bin/

RUN mkdir /opt/jupyterhub_cost_monitoring
COPY . /opt/jupyterhub_cost_monitoring
WORKDIR /opt/jupyterhub_cost_monitoring
RUN uv sync --locked
ENV PATH="/opt/jupyterhub_cost_monitoring/.venv/bin:$PATH"

WORKDIR /opt/jupyterhub_cost_monitoring/src/jupyterhub_cost_monitoring
USER 65534
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["flask", "run", "--port", "8080", "--host", "0.0.0.0"]