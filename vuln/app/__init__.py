from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
from app.config import Config 
from prometheus_flask_exporter import PrometheusMetrics

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Menggunakan konfigurasi dari config.py

    db.init_app(app)

    api = Api(app, version="1.0", title="Vulnerable API", description="API for Security Testing")

    metrics = PrometheusMetrics(app)

    from app.routes import ns
    api.add_namespace(ns)

    return app
