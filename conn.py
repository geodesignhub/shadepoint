
from os import environ as env
from redis import ConnectionPool, Redis

import logging
logger = logging.getLogger("local-climate-response")

def get_redis():
    # A method to get the redis instance and is used globally
    redis_url = env.get("REDIS_URL", "redis://local.test:6379")
    connection_pool = ConnectionPool.from_url(redis_url)
    redis = Redis(connection_pool=connection_pool, ssl_cert_reqs=None)
    return redis
