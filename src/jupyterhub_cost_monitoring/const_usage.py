"""
Constants used to query Prometheus for JupyterHub usage data.
"""

MEMORY_REQUESTS_PER_USER = """
    label_replace(
        sum(
        kube_pod_container_resource_requests{resource="memory"} * on (namespace, pod)
        group_left(annotation_hub_jupyter_org_username) group(
            kube_pod_annotations{annotation_hub_jupyter_org_username!=""}
            ) by (pod, namespace, annotation_hub_jupyter_org_username)
        ) by (annotation_hub_jupyter_org_username, namespace),
        "username", "$1", "annotation_hub_jupyter_org_username", "(.*)"
    )
"""

STORAGE_USAGE_PER_USER = """
    label_replace(
        sum(dirsize_total_size_bytes{namespace!=""}) by (namespace, directory),
        "username", "$1", "directory", "(.*)"
    )
"""

# Time step for Prometheus queries: "5m" for compute since user pods come and go on this timescale, "1d" for home storage since we do not need to track changes in storage usage more frequently than daily.
USAGE_MAP = {
    "compute": {
        "query": MEMORY_REQUESTS_PER_USER,
        "step": "5m",
    },
    "home storage": {
        "query": STORAGE_USAGE_PER_USER,
        "step": "1d",
    },
}
