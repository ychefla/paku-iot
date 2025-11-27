FROM grafana/grafana:11.3.0

# Copy Grafana provisioning files (datasources and dashboard provider config)
COPY provisioning /etc/grafana/provisioning

# Copy dashboard JSON files to a separate location that is not covered by the volume
COPY dashboards /etc/grafana/dashboards
