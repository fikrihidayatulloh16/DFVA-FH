# app/decorators.py (buat file baru ini atau letakkan di utils.py)
from functools import wraps
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask import jsonify # Atau dari flask_restx untuk response yang konsisten

def roles_required(required_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request() # Pastikan token valid dan ada
            claims = get_jwt()
            user_roles = claims.get("role", "") # Ambil role dari token, default string kosong
            
            # Jika role di token adalah string tunggal
            if isinstance(user_roles, str):
                user_roles = [user_roles] # Ubah jadi list untuk pengecekan
            
            # Periksa apakah ada role pengguna yang cocok dengan role yang dibutuhkan
            if not any(role in user_roles for role in required_roles):
                # Gunakan logger di sini
                # logger.warning(f"User with roles {user_roles} denied access to resource requiring roles {required_roles}")
                return {"message": "Akses ditolak: Peran tidak memadai"}, 403 # ns.abort(403, message="...") jika pakai Flask-RESTX
            return fn(*args, **kwargs)
        return wrapper
    return decorator