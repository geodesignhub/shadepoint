import redis
from os import environ as env

def get_redis():
    # A method to get the redis instance and is used globally
    redis_url = env.get('REDIS_URL','redis://local.test:6379')    
    r = redis.from_url(redis_url)
    return r
