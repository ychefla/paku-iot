FROM postgres:16-alpine

# Default configuration for development.
ENV POSTGRES_USER=paku
ENV POSTGRES_PASSWORD=paku
ENV POSTGRES_DB=paku

# Copy initialization script to be executed on first startup
# Scripts in docker-entrypoint-initdb.d are automatically executed
# in alphabetical order when the container starts for the first time.
COPY init.sql /docker-entrypoint-initdb.d/

# Keep the container running for now.
CMD ["postgres"]
