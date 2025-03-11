# Use Python 3.10.16 slim image
FROM python:3.10.16-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (including Redis)
RUN apt-get update && apt-get install -y \
    build-essential \
    libkrb5-dev \
    gcc \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code and the start script
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Expose the port (Railway expects PORT environment variable)
EXPOSE 8080
EXPOSE 5000

# Set default environment variables (can be overridden by Railway)
ENV PORT=8080
ENV REDIS_URL=redis://localhost:6379/0
ENV FLASK_RUN_PORT=${PORT}
ENV FLASK_RUN_HOST=0.0.0.0

# Run the start script
CMD ["./start.sh"]
