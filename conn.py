import redis
from os import environ as env

def get_redis():
    # A method to get the redis instance and is used globally
    redis_host = env.get('REDIS_HOST', "local.test")
    redis_port = env.get('REDIS_PORT', 6379)
    redis_password = env.get('REDIS_PASSWORD', None)
    
    if redis_password:
        r = redis.Redis(host=redis_host, port=redis_port, password = redis_password, charset="utf-8",decode_responses=True)
    else:
        r = redis.Redis(host=redis_host, port=redis_port, charset="utf-8",decode_responses=True)

    return r
