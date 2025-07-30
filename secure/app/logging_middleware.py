# logging_middleware.py
from flask import request, g, session
from .logger import get_logger
import time
import os
import logging

# Inisialisasi logger utama untuk API
api_logger = get_logger('api_logger')

# Inisialisasi logger khusus untuk metrics
def get_metrics_logger():
    logger = logging.getLogger('metrics_logger')
    if not logger.hasHandlers():
        if not os.path.exists("logs"):
            os.makedirs("logs")
        handler = logging.FileHandler("logs/metrics.log")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - metrics_logger - %(message)s")
        handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger

metrics_logger = get_metrics_logger()

def init_logging_middleware(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        duration = round(time.time() - g.start_time, 4)
        ip = request.remote_addr
        method = request.method
        path = request.path
        status = response.status_code
        user_agent = request.headers.get("User-Agent", "-")
        username = session.get("username", "-")

        log_line = f"{ip} | {method} {path} | Status: {status} | Time: {duration}s | User-Agent: {user_agent} | User: {username}"

        # Logging berdasarkan path
        if path.startswith("/metrics") or path.startswith("/users/custom-metrics"):
            if 400 <= status < 500:
                metrics_logger.warning(log_line)
            elif 500 <= status < 600:
                metrics_logger.error(log_line)
            else:
                metrics_logger.info(log_line)
        else:
            if 400 <= status < 500:
                api_logger.warning(log_line)
            elif 500 <= status < 600:
                api_logger.error(log_line)
            else:
                api_logger.info(log_line)

        return response