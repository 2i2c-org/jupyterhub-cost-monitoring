import os

from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware

metrics_prefix = os.getenv(
    "COST_MONITORING_METRICS_PREFIX", "jupyterhub_cost_monitoring"
)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of http requests",
    ["method", "code", "endpoint"],
    namespace=metrics_prefix,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to instrument HTTP request metrics for Prometheus with every request.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            code=str(response.status_code),
        ).inc()

        return response
