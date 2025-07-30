import sqlite3

conn = sqlite3.connect("instance/database.db")
cursor = conn.cursor()

# Menampilkan semua user (jika ada)
cursor.execute("SELECT * FROM user;")
users = cursor.fetchall()

print("Data User:", users)

conn.close()
