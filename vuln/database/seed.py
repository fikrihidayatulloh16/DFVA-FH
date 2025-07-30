from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    user1 = User(username="admin", password="admin123", role="admin", description="ini adalah admin")  # ⚠️ Password tidak di-hash
    user2 = User(username="user", password="user123", role="user", description="ini adalah user ke 1")   # ⚠️ Password mudah ditebak
    user3 = User(username="user2", password="user2123", role="user", description="ini adalah user ke 2")   # ⚠️ Password mudah ditebak

    db.session.add(user1)
    db.session.add(user2)
    db.session.add(user3)
    db.session.commit()

    print("Data user berhasil ditambahkan!")
