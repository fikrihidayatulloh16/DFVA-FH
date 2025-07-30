from app import db  # Pastikan ini tidak menyebabkan circular import
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Hapus kolom password lama jika ada (misal: password = db.Column(db.String(120), nullable=False))
    password_hash = db.Column(db.String(256), nullable=False) # Kolom untuk menyimpan hash password
    role = db.Column(db.String(80), nullable=False, default='user') # Misal: 'user', 'admin'
    description = db.Column(db.String(500), nullable=True)

    def set_password(self, password):
        # Buat hash password dengan metode yang lebih aman, misal bcrypt atau scrypt jika didukung
        # werkzeug defaultnya pbkdf2:sha256, tapi bisa dikonfigurasi
        # Untuk keamanan lebih, pertimbangkan method seperti "pbkdf2:sha256:260000" atau "scrypt:32768:8:1"
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:260000')


    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
