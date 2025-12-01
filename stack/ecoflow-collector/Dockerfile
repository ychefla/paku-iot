FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ecoflow_collector.py .

# Run the collector
CMD ["python", "-u", "ecoflow_collector.py"]
