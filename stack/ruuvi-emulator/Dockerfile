FROM python:3.12-alpine

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the emulator script
COPY emulator.py .

# Run the emulator
CMD ["python", "emulator.py"]
