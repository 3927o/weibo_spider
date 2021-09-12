import redis
import requests

from settings import REDIS_HOST, REDIS_PORT


pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT)


def get_redis_conn():
    return redis.Redis(connection_pool=pool)


def get_proxy():
    resp = requests.get("http://121.41.201.68:5010/pop").json()
    proxy = {
        "http": resp["proxy"]
        # "https": resp["proxy"]
    }
    return proxy
