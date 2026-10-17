FROM grafana/grafana:11.3.0

# Copy Grafana provisioning files (datasources and dashboard provider config)
COPY provisioning /etc/grafana/provisioning

# Copy dashboard JSON files to a separate location that is not covered by the volume
COPY dashboards /etc/grafana/dashboards
COPY dashboards_legacy /etc/grafana/dashboards_legacy

# Alert notifications are rendered from env vars at startup (see entrypoint.sh)
USER root
COPY alerting-notifications.yaml.tmpl /etc/grafana/alerting-notifications.yaml.tmpl
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R 472:0 /etc/grafana/provisioning/alerting
USER 472

ENTRYPOINT ["/entrypoint.sh"]
