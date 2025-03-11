#!/bin/bash

# Set default port if not provided
PORT=${PORT:-8080}
REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}

echo "Starting services with PORT=${PORT} and REDIS_URL=${REDIS_URL}"

# Start Redis in the background
echo "Starting Redis..."
redis-server &

# Start the worker in the background with the Redis URL
echo "Starting Worker..."
REDIS_URL=${REDIS_URL} python worker.py &

# Start the Flask app in the foreground using Gunicorn
echo "Starting Flask App..."
gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --threads 2 --timeout 120
