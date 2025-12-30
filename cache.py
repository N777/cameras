import pickle
from datetime import timedelta

import redis

from evo import get_stream_urls, get_frame_from_stream

REDIS = redis.Redis(host='redis', port=6379, db=0)

def update_images_in_cache():
    stream_urls = get_stream_urls()
    frames = [get_frame_from_stream(stream_url) for stream_url in stream_urls.values()]
    set_images_in_cache(frames)


def set_images_in_cache(frames):
    REDIS.setex('EVO_IMAGES', timedelta(minutes=20), pickle.dumps(frames))


def get_images_from_cache():
    cached_images = REDIS.get('EVO_IMAGES')
    if cached_images is None:
        return []
    return pickle.loads(cached_images)

