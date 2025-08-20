"""
Constants used to query Prometheus for JupyterHub usage data.
"""

# Resolution for Prometheus queries
# For MEMORY_REQUESTS_PER_USER this needs to be a small value because pods can be created and deleted frequently.
# And we want to capture the memory requests for each pod as they are created.
TIME_RESOLUTION = "5m"

MEMORY_REQUESTS_PER_USER = """
    label_replace(
        sum(
            kube_pod_container_resource_requests{resource="memory", namespace=~".*", pod=~"jupyter-.*"} * on (namespace, pod)
            group_left(annotation_hub_jupyter_org_username) group(
                kube_pod_annotations{namespace=~".*", annotation_hub_jupyter_org_username=~".*"}
            ) by (pod, namespace, annotation_hub_jupyter_org_username)
        ) by (annotation_hub_jupyter_org_username, namespace),
        "username", "$1", "annotation_hub_jupyter_org_username", "(.*)"
    )
"""

STORAGE_USAGE_PER_USER = """
    label_replace(
        sum(dirsize_total_size_bytes{namespace=~".*"}) by (namespace, directory),
        "username", "$1", "directory", "(.*)"
    )
"""


USAGE_MAP = {
    "compute": MEMORY_REQUESTS_PER_USER,
    "home storage": STORAGE_USAGE_PER_USER,
}
