import sqlite3
from datetime import datetime

conn = sqlite3.connect("pln_kwh.db")
c = conn.cursor()

# Setel created_at agar tidak kosong (null) yang bikin error tabel di React
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
c.execute("UPDATE users SET created_at = ? WHERE username = 'admin'", (now,))
conn.commit()

print("Beres! Bug tabel kosong sudah diperbaiki!")
