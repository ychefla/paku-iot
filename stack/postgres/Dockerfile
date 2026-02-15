FROM postgres:16-alpine

# Environment variables for database configuration are passed from docker-compose.
# See .env.example for required variables:
#   - POSTGRES_USER
#   - POSTGRES_PASSWORD
#   - POSTGRES_DB

# Copy the initialization scripts
# Postgres will automatically execute .sql files in /docker-entrypoint-initdb.d/
# in alphabetical order
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY ota_schema.sql /docker-entrypoint-initdb.d/02-ota_schema.sql
COPY edge_devices_schema.sql /docker-entrypoint-initdb.d/03-edge_devices_schema.sql

# Backup script (invoked by pg-backup service or manual docker exec)
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

CMD ["postgres"]
