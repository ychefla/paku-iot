FROM postgres:16-alpine

# Default configuration for development.
ENV POSTGRES_USER=paku
ENV POSTGRES_PASSWORD=paku
ENV POSTGRES_DB=paku

# Copy the initialization script
# Postgres will automatically execute .sql files in /docker-entrypoint-initdb.d/
COPY init.sql /docker-entrypoint-initdb.d/

CMD ["postgres"]
