FROM postgres:16-alpine

# Default configuration for development.
ENV POSTGRES_USER=paku
ENV POSTGRES_PASSWORD=paku
ENV POSTGRES_DB=paku

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Keep the container running for now.
CMD ["postgres"]
