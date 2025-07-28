# Helm chart repository for jupyterhub-cost-monitoring

This is a bare Helm chart repository specifically for the [jupyterhub-cost-monitoring](https://github.com/2i2c-org/jupyterhub-cost-monitoring) chart.

{% for chartmap in site.data.index.entries %}
## Releases: {{ chartmap[0] }}

| Version | Date | App. version |
|---------|------|---------------------|
  {%- assign sortedcharts = chartmap[1] | sort: 'created' | reverse %}
  {%- for chart in sortedcharts %}
| [{{ chart.version }}]({{ chart.urls[0] }}) | {{ chart.created | date_to_long_string }} | {{ chart.appVersion }} |
  {%- endfor %}
{%- endfor %}