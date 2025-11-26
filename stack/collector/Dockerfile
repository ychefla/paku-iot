FROM python:3.12-alpine

# Install system dependencies required by psycopg[binary]
RUN apk add --no-cache gcc musl-dev libpq-dev

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector source code
COPY collector.py .

# Default command: run the collector
CMD ["python", "collector.py"]
