"""
Constants used to query Prometheus for JupyterHub usage data.
"""

TIME_RESOLUTION = "5m"

MEMORY_REQUESTS_PER_USER = """
    sum(
        kube_pod_container_resource_requests{resource=\"memory\", namespace=~\".*\", pod=~\"jupyter-.*\"}  * on (namespace, pod)
        group_left(annotation_hub_jupyter_org_username) group(
            kube_pod_annotations{namespace=~\".*\", annotation_hub_jupyter_org_username=~\".*\"}
            ) by (pod, namespace, annotation_hub_jupyter_org_username)
    ) by (annotation_hub_jupyter_org_username, namespace)
"""

USAGE_MAP = {
    "compute": MEMORY_REQUESTS_PER_USER,
}
