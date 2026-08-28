FROM python:3.14-slim-bookworm

RUN apt-get update && apt-get install -y tini git curl vim

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir /opt/jupyterhub_cost_monitoring
COPY pyproject.toml /opt/jupyterhub_cost_monitoring
COPY LICENSE.md /opt/jupyterhub_cost_monitoring
COPY README.md /opt/jupyterhub_cost_monitoring
COPY src/jupyterhub_cost_monitoring /opt/jupyterhub_cost_monitoring/src/jupyterhub_cost_monitoring

WORKDIR /opt/jupyterhub_cost_monitoring
RUN pip install -e .

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["fastapi", "run", "src/jupyterhub_cost_monitoring/app.py", "--port", "8080", "--host", "0.0.0.0"]