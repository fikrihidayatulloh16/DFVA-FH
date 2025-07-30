# monitor.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import request, Response, g
import time

# Counter: menghitung total request berdasarkan method dan status
REQUEST_COUNTER = Counter(
    'flask_api_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'http_status']
)

# Histogram: mengukur waktu respons berdasarkan method dan endpoint
REQUEST_LATENCY = Histogram(
    'flask_api_request_duration_seconds',
    'Latency of HTTP requests in seconds',
    ['method', 'endpoint']
)

def setup_metrics(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def record_metrics(response):
        request_latency = time.time() - g.start_time
        REQUEST_LATENCY.labels(request.method, request.path).observe(request_latency)
        REQUEST_COUNTER.labels(request.method, request.path, response.status_code).inc()
        return response

    # Endpoint untuk expose /custom-metrics
    @app.route('/users/custom-metrics')
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
