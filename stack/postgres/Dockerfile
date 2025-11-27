FROM postgres:16-alpine

# Environment variables for database configuration are passed from docker-compose.
# See .env.example for required variables:
#   - POSTGRES_USER
#   - POSTGRES_PASSWORD
#   - POSTGRES_DB

# Copy the initialization script
# Postgres will automatically execute .sql files in /docker-entrypoint-initdb.d/
COPY init.sql /docker-entrypoint-initdb.d/

CMD ["postgres"]
