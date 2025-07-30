from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from app import db
from app.models import User
from time import time
from sqlalchemy import text
from app.limiter import limiter
import logging
from datetime import datetime
from flask_limiter.util import get_remote_address
import html  # untuk sanitasi sederhana
import re
from werkzeug.security import generate_password_hash, check_password_hash # Sebenarnya tidak perlu di sini jika sudah di model
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app.decorators import roles_required
from app.schemas import UserSchema
from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
from app.throttling import throttle_after_limit

ns = Namespace("users", description="User operations")
ds = Namespace("dashboard", description="Dashboard operation")

# Definisikan model input sederhana untuk dokumentasi Swagger (opsional tapi bagus)
search_model = ns.model('UserSearch', {
    'search_term': fields.String(required=True, description='Bagian username yang dicari')
})

login_model = ns.model('Login', { # Definisikan model untuk request body login
    'username': fields.String(required=True, description='Username pengguna'),
    'password': fields.String(required=True, description='Password pengguna')
})

# Model untuk update deskripsi
description_model = ns.model('UserDescription', {
    'description': fields.String(description='Deskripsi profil pengguna')
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_schema = UserSchema()

REQUEST_COUNT = Counter('my_app_requests_total', 'Total number of requests')

@ns.route("/")
class UserList(Resource):
    def get(self):
        """Menampilkan semua user"""
        users = User.query.all()
        return jsonify([{"id": u.id, "username": u.username, "role": u.role, "description": u.description} for u in users])

@ns.route('/custom-metrics')
class Metric(Resource):
    def get(self):
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@ns.route('/login-rate')
class LoginRate(Resource):
    @limiter.limit(
        "20 per minute",
        deduct_when=lambda response: response.status_code == 200  # Deduct only on successful requests
    )
    def post(self):
        from datetime import datetime
        print(f"Request at {datetime.now()} from {get_remote_address()}")
        return {"message": "Login attempt OK"}


@ns.route("/<int:id>") # Sebaiknya endpoint ini untuk admin atau penggunaan sangat spesifik
class UserDetail(Resource):
    @jwt_required() # Lindungi juga endpoint ini
    @roles_required(['admin']) # Contoh: Hanya admin yang boleh lihat detail semua user
    def get(self, id):
        """Menampilkan detail user berdasarkan ID (HANYA UNTUK ADMIN)"""
        # current_admin_id = get_jwt_identity() # Bisa di-log siapa yang mengakses
        user = User.query.get(id)
        if not user:
            return {"message": "User tidak ditemukan"}, 404
        
        # JANGAN PERNAH KEMBALIKAN PASSWORD HASH
        return jsonify({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "description": html.escape(user.description) if user.description else ""
        })
    
@ns.route('/profile')
class UserProfileResource(Resource):
    @jwt_required()
    def get(self):
        print(get_jwt())  # debug: lihat semua claim
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))  # Pastikan dikonversi kembali ke int
        print("User ID dari JWT:", user_id)
        if not user:
            return {"message": "User tidak ditemukan"}, 404
        return user_schema.dump(user), 200


        user = User.query.get(current_user_id)

@ns.route('/login')
class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            return {"message": "Username atau password salah"}, 401

        access_token = access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})

        return {"access_token": access_token}, 200

    
# --- ENDPOINT SQL INJECTION BARU ---
@ns.route("/search")
class UserSearch(Resource):
    @ns.expect(search_model)
    def post(self):
        """Cari user berdasarkan bagian nama, dengan validasi input"""
        data = request.get_json()
        allowed_fields = {"search_term"}
        if not set(data.keys()).issubset(allowed_fields):
            return {"message": "Field tidak diizinkan"}, 400

        search_term = data.get("search_term", "")
        if not search_term:
            return {"message": "Parameter 'search_term' dibutuhkan"}, 400

        # ✅ Regex: hanya huruf dan angka, 1–20 karakter
        if not re.fullmatch(r"[a-zA-Z0-9]{1,20}", search_term):
            return {"message": "Format pencarian tidak valid"}, 400

        try:
            # ✅ Gunakan ORM + LIKE (dengan sanitasi by default)
            users = User.query.filter(User.username.ilike(f"%{search_term}%")).all()
            if not users:
                return {"message": f"Tidak ada user ditemukan dengan term: '{search_term}'"}, 404
            return jsonify([{"id": u.id, "username": u.username, "role": u.role} for u in users])
        except Exception as e:
            print(f"Database error during search: {e}")
            return {"message": "Terjadi error saat pencarian"}, 500

        
# --- ENDPOINT XSS BARU (Stored) ---
@ns.route("/<int:target_user_id>/description") # Endpoint ini tetap ada jika admin boleh edit deskripsi orang lain
class UserDescription(Resource):
    @jwt_required() # Memerlukan login
    @ns.expect(description_model)
    def put(self, target_user_id):
        """Update deskripsi user (memerlukan otentikasi & otorisasi)"""
        current_user_id = get_jwt_identity()
        claims = get_jwt() # Dapatkan semua claims dari token
        current_user_role = claims.get("role")

        user_to_update = User.query.get(target_user_id)
        if not user_to_update:
            return {"message": "User yang akan diupdate tidak ditemukan"}, 404

        # Otorisasi: Hanya user sendiri ATAU admin yang boleh edit
        if current_user_id != target_user_id and current_user_role != 'admin':
            logger.warning(f"User ID {current_user_id} (role: {current_user_role}) unauthorized to update description for user ID {target_user_id}.")
            return {"message": "Tidak diizinkan mengupdate deskripsi pengguna lain"}, 403

        data = request.get_json()
        # Whitelisting field (sudah Anda implementasikan sebelumnya, bisa dipertahankan)
        allowed_fields = {"description"}
        if not set(data.keys()).issubset(allowed_fields):
            return {"message": "Field tidak diizinkan"}, 400

        new_description = data.get("description", "")
        if len(new_description) > 500: # Validasi panjang
            return {"message": "Deskripsi terlalu panjang (maks 500 karakter)"}, 400

        sanitized_desc = html.escape(new_description) # Sanitasi XSS
        user_to_update.description = sanitized_desc
        
        try:
            db.session.commit()
            logger.info(f"User ID {current_user_id} updated description for user ID {target_user_id}.")
            return {"message": f"Deskripsi untuk user {user_to_update.username} berhasil diupdate."}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating description for user ID {target_user_id} by user ID {current_user_id}: {e}")
            return {"message": "Gagal mengupdate deskripsi"}, 500

@ds.route("/dashboard")
class Dashboard(Resource): # <<< Tambahkan (Resource) di sini
    def get(self):
        return {"hallo":"ini halaman dashboard"}
    
@ns.route('/admin-panel')
class AdminPanel(Resource):
    @jwt_required() # Pertama, pastikan user terotentikasi
    @roles_required(['admin']) # Kemudian, pastikan user memiliki peran 'admin'
    def get(self):
        current_user_identity = get_jwt_identity() # Ini adalah user.id
        claims = get_jwt()
        user_role = claims.get("role")
        
        # Anda bisa mengambil username dari DB jika perlu, karena identity hanya user.id
        admin_user = User.query.get(current_user_identity)
        logger.info(f"Admin user {admin_user.username} (role: {user_role}) accessed admin panel.")
        return {"message": f"Halo admin {admin_user.username}, ini halaman admin yang aman!"}

@ns.route('/hello')
class Hello(Resource):
    def get(self):
        start = time()
        result = {"message": "Hello World"}
        duration = round(time() - start, 5)
        print(f"Request completed in {duration} seconds")
        return result
