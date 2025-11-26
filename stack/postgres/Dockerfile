FROM postgres:16-alpine

# Environment variables for database configuration are passed from docker-compose.
# See .env.example for required variables:
#   - POSTGRES_USER
#   - POSTGRES_PASSWORD
#   - POSTGRES_DB

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Keep the container running for now.
CMD ["postgres"]
