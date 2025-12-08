FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ota_service.py .

# Create firmware storage directory
RUN mkdir -p /firmware

# Expose API port
EXPOSE 8080

# Run the service
CMD ["python", "ota_service.py"]
