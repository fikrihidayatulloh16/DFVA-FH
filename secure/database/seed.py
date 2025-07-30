from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Hapus user lama jika ada (opsional, untuk menghindari duplikasi saat seeding)
    User.query.filter_by(username='admin').delete()
    User.query.filter_by(username='user').delete()
    User.query.filter_by(username='user2').delete()
    db.session.commit()

    user1 = User(username="admin", role="admin", description="ini adalah admin")
    user1.set_password("admin123") # <<< GUNAKAN set_password()

    user2 = User(username="user", role="user", description="ini adalah user ke 1")
    user2.set_password("user123")  # <<< GUNAKAN set_password()

    user3 = User(username="user2", role="user", description="ini adalah user ke 2")
    user3.set_password("user2123") # <<< GUNAKAN set_password()

    db.session.add(user1)
    db.session.add(user2)
    db.session.add(user3)
    db.session.commit()

    print("Data user berhasil ditambahkan!")