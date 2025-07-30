from app import db  # Pastikan ini tidak menyebabkan circular import

class User(db.Model):  # Harusnya db.Model sudah terdefinisi dengan benar
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # 🔴 Vulnerable: Password tidak di-hash
    role = db.Column(db.String(20), nullable=False, default='user')  # Bisa 'admin' atau 'user'
    description = db.Column(db.Text, nullable=True) # <-- Kolom Bar

    def __repr__(self):
        return f"<User {self.username}>"
