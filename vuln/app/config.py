import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SESSION_COOKIE_SAMESITE = "Lax"
    SECRET_KEY = "your_secret_key"  # Ganti dengan key yang aman
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, '../instance/database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
