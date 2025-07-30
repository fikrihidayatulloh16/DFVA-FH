import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import redis
from app.logger import get_logger
import time

# Setup logging
logger = get_logger("rate_limit")

# Gunakan host redis dari environment variable atau default ke 'redis'
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')

MAX_RETRIES = 200
RETRY_DELAY = 2  # detik

# redis client
redis_connection = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    db=0,
    socket_timeout=5,
    socket_connect_timeout=5,
    decode_responses=True
)

# Konfigurasi Limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{REDIS_HOST}:6379/0",
    storage_options={"socket_connect_timeout": 5, "retry_on_timeout": True},
    strategy="moving-window",
    headers_enabled=True,
    on_breach=lambda limiter: logger.warning(f"Rate limit breached: {limiter}")
)

# Test koneksi
for attempt in range(MAX_RETRIES):
    try:
        redis_connection.ping()
        logger.info("✅ Redis connected successfully")
        break
    except redis.ConnectionError:
        logger.error(f"❌ Failed to connect to Redis (attempt {attempt+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
else:
    logger.critical("❌❌ Redis connection failed after multiple attempts")
