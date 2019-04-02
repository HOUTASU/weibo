import redis
from scrapy.utils.project import get_project_settings


def get_redis_client():
    setting = get_project_settings()
    pool = redis.ConnectionPool(host=setting.get('REDIS_HOST'), password=setting.get('REDIS_PASSWORD'),
                                port=setting.get('REDIS_PORT'), decode_responses=True)
    client = redis.Redis(connection_pool=pool)
    return client
