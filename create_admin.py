import sqlite3
from passlib.context import CryptContext

conn = sqlite3.connect("pln_kwh.db")
pwd = CryptContext(schemes=["bcrypt"]).hash("admin123")
conn.execute("INSERT INTO users (username, password_hash, full_name, role, is_active) VALUES ('admin', ?, 'Administrator', 'admin', 1)", (pwd,))
conn.commit()
print("SUKSES! Silakan login di web dengan Username: admin | Password: admin123")
