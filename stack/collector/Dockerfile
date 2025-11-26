FROM python:3.12-alpine

# Install dependencies
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the collector script
COPY collector.py .

# Run the collector service
CMD ["python", "collector.py"]
