FROM grafana/grafana:11.0.0

# Copy provisioning configuration
COPY provisioning/datasources/ /etc/grafana/provisioning/datasources/
COPY provisioning/dashboards/ /etc/grafana/provisioning/dashboards/

# Disable login for development (admin user auto-login)
ENV GF_AUTH_ANONYMOUS_ENABLED=true
ENV GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin

# Expose Grafana port
EXPOSE 3000
