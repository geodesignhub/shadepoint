"""
Worker script for local climate response.
"""

import os
import logging
import redis
from rq import Worker, Queue

logger = logging.getLogger("local-climate-response")

listen = ["high", "default", "low"]

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

conn = redis.from_url(redis_url)

if __name__ == "__main__":
    worker = Worker(listen, connection=conn)
    worker.work()
