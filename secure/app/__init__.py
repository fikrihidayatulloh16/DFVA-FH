from flask import Flask, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
from app.config import Config 
from app.logging_middleware import init_logging_middleware
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from prometheus_flask_exporter import PrometheusMetrics
from .throttling import init_throttling
from app.monitor import setup_metrics

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    from .limiter import limiter
    limiter.init_app(app)
    
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    init_logging_middleware(app)

    init_throttling(app)

    setup_metrics(app)

    # Monitoring Prometheus
    from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
    metrics = PrometheusMetrics(app)

    api = Api(app, version="1.0", title="Vulnerable API", description="API for Security Testing")

    # Optional: exclude /metrics dari metrics itu sendiri
    metrics.exclude_all_metrics()
    metrics.info('app_info', 'Flask app info', version='1.0.0')

    from app.routes import ns
    api.add_namespace(ns, path="/users")

    @app.route('/')
    def index():
        return redirect('/docs')

    return app
