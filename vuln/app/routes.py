from flask import request, jsonify, session
from flask_restx import Namespace, Resource, fields
from app import db
from app.models import User
from time import time
from sqlalchemy import text
from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

ns = Namespace("users", description="User operations")
ds = Namespace("dashboard", description="Dashboard operation")

# Definisikan model input sederhana untuk dokumentasi Swagger (opsional tapi bagus)
search_model = ns.model('UserSearch', {
    'search_term': fields.String(required=True, description='Bagian username yang dicari')
})

# Model untuk update deskripsi
description_model = ns.model('UserDescription', {
    'description': fields.String(description='Deskripsi profil pengguna')
})

@ns.route("/")
class UserList(Resource):
    def get(self):
        """Menampilkan semua user"""
        users = User.query.all()
        return jsonify([{"id": u.id, "username": u.username, "role": u.role, "description": u.description} for u in users])

@ns.route("/<int:id>")
class UserDetail(Resource):
    def get(self, id):
        """Menampilkan detail user berdasarkan ID (termasuk deskripsi & password!)"""
        user = User.query.get(id)
        if not user:
            return {"message": "User tidak ditemukan"}, 404
        # 🔴 VULNERABLE: Mengembalikan password dan deskripsi mentah
        return jsonify({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "description": user.description # Kembalikan deskripsi
        })
    
@ns.route('/profile/<int:user_id>')
class UserProfile(Resource):
    def get(self, user_id):
        # Tidak ada autentikasi atau pengecekan apakah ini user yang benar
        user = User.query.get(user_id)
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "description": user.description
            }
        return {"message": "User not found"}, 404

@ns.route('/custom-metrics')
class Metric(Resource):
    def get(self):
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@ns.route("/login")
class UserLogin(Resource):
    def post(self):
        """Login user dengan query yang rentan (hanya untuk pengujian)"""
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        # QUERY RAW SQL YANG RENTAN
        sql = text(f"SELECT * FROM user WHERE username='{username}' AND password='{password}'")
        result = db.session.execute(sql).fetchone()
        
        if result:
            return {"message": "Login berhasil!", "user": {"id": result[0], "username": result[1]}}
        return {"message": "Login gagal!"}, 401

@ns.route('/login-rate')
class LoginRateVulnerable(Resource):
    def post(self):
        """
        Endpoint vulnerable: tidak ada rate limiting.
        Dapat digunakan untuk simulasi brute-force attack.
        """
        return {"message": "Login attempt OK (no rate limit)"}
    
# --- ENDPOINT SQL INJECTION BARU ---
@ns.route("/search")
class UserSearch(Resource):
    # Kita bisa pakai GET dengan query param atau POST dengan JSON body. Mari pakai POST.
    @ns.expect(search_model) # Memberi tahu Swagger input yang diharapkan
    def post(self):
        """
        Mencari user berdasarkan bagian username (RENTAH SQL Injection).
        Contoh Body: {"search_term": "min"}
        """
        data = request.get_json()
        search_term = data.get("search_term")

        if not search_term:
            return {"message": "Parameter 'search_term' dibutuhkan"}, 400

        # 🔴 VULNERABLE: Membangun query SQL mentah dengan input pengguna
        # Menggunakan LIKE untuk mencari bagian nama
        sql_query = text(f"SELECT id, username, role FROM user WHERE username = '{search_term}'")

        try:
            results = db.session.execute(sql_query).fetchall()
            # Format hasil agar lebih mudah dibaca
            users_found = [{"id": row[0], "username": row[1], "role": row[2]} for row in results]
            if not users_found:
                return {"message": f"Tidak ada user ditemukan dengan term: '{search_term}'"}, 404
            return jsonify(users_found) # Return hasil pencarian
        except Exception as e:
            # Penting: Jangan bocorkan detail error SQL ke pengguna di produksi
            print(f"Database error during search: {e}") # Log error untuk debug
            return {"message": "Terjadi error saat pencarian"}, 500
        
# --- ENDPOINT XSS BARU (Stored) ---
@ns.route("/<int:id>/description")
class UserDescription(Resource):
    @ns.expect(description_model)
    def put(self, id):
        """
        Mengupdate deskripsi profil user (RENTAH Stored XSS).
        Membutuhkan body JSON: {"description": "Teks deskripsi <script>..."}
        (Tidak ada Autentikasi/Otorisasi di sini!)
        """
        user = User.query.get(id)
        if not user:
            return {"message": "User tidak ditemukan"}, 404

        data = request.get_json()
        new_description = data.get("description")

        # 🔴 VULNERABLE: Menyimpan input mentah ke database tanpa sanitasi
        user.description = new_description
        try:
            db.session.commit()
            return {"message": f"Deskripsi untuk user {user.username} berhasil diupdate."}
        except Exception as e:
            db.session.rollback()
            print(f"Error updating description: {e}")
            return {"message": "Gagal mengupdate deskripsi"}, 500

@ds.route("/dashboard")
class Dashboard():
    def get(self):
        return {"hallo":"ini halaman dashboard"}
    
@ns.route('/admin-panel')
class AdminPanel(Resource):
    def get(self):
        # Simulasi input dari user (username dikirim dari client, rentan)
        username = request.args.get('username')
        user = User.query.filter_by(username=username).first()

        if not user:
            return {"message": "User tidak ditemukan"}, 404

        # ✅ Ada pengecekan role, tapi input username dari client masih bisa dimanipulasi
        if user.role == "admin":
            return {"message": f"Halo admin {user.username}, ini halaman admin"}
        else:
            return {"message": "Kamu tidak punya akses ke halaman ini"}, 403

@ns.route('/hello')
class Hello(Resource):
    def get(self):
        start = time()
        result = {"message": "Hello World"}
        duration = round(time() - start, 5)
        print(f"Request completed in {duration} seconds")
        return result

@ns.route('/session-login')
class SessionLogin(Resource):
    def post(self):
        """
        Simulasi login yang menyimpan session.
        Ini memicu penggunaan SESSION_COOKIE_HTTPONLY, SAMESITE, dan itsdangerous.
        """
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        # Gunakan raw SQL rentan seperti di /login
        sql = text(f"SELECT * FROM user WHERE username='{username}' AND password='{password}'")
        result = db.session.execute(sql).fetchone()

        if result:
            # Simpan ke session
            session['username'] = result[1]  # result[1] adalah username
            session['user_id'] = result[0]   # simpan ID juga jika diperlukan
            return {
                "message": "Login berhasil dengan session!",
                "user": {"id": result[0], "username": result[1]}
            }
        return {"message": "Login gagal!"}, 401

