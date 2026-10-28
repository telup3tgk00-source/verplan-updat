import sqlite3
from passlib.context import CryptContext

# Inisialisasi passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash("admin123")

# Koneksi ke database
conn = sqlite3.connect("pln_kwh.db")
c = conn.cursor()

# Cek apakah admin ada
c.execute("SELECT * FROM users WHERE username = 'admin'")
admin = c.fetchone()

if admin:
    # Update password
    c.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (hashed_password,))
    conn.commit()
    print("Password berhasil direset ke: admin123")
else:
    print("User admin tidak ditemukan di database.")

conn.close()
