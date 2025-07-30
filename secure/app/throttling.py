import redis
import time
import os
from flask import request
from functools import wraps

# Konfigurasi Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")  # Ganti ke "redis" jika pakai docker-compose
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# Konstanta throttling
THROTTLE_LIMIT = 20         # batas akses sebelum throttling
THROTTLE_DELAY = 1          # delay dalam detik setelah melewati batas
THROTTLE_WINDOW = 60        # window waktu dalam detik

# Decorator untuk throttling per endpoint
def throttle_after_limit():
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr
            key = f"throttle_counter:{ip}"
            current = redis_client.get(key)

            if current is None:
                redis_client.set(key, 1, ex=THROTTLE_WINDOW)
            else:
                current = int(current) + 1
                redis_client.set(key, current, ex=THROTTLE_WINDOW)
                if current > THROTTLE_LIMIT:
                    time.sleep(THROTTLE_DELAY)

            return f(*args, **kwargs)
        return wrapper
    return decorator

# Fungsi init untuk global throttling (opsional)
def init_throttling(app):
    @app.before_request
    def dynamic_throttling():
        ip = request.remote_addr
        key = f"throttle_counter:{ip}"
        current = redis_client.get(key)

        if current is None:
            redis_client.set(key, 1, ex=THROTTLE_WINDOW)
        else:
            current = int(current) + 1
            redis_client.set(key, current, ex=THROTTLE_WINDOW)
            if current > THROTTLE_LIMIT:
                time.sleep(THROTTLE_DELAY)
