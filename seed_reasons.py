import sqlite3

conn = sqlite3.connect("pln_kwh.db")
c = conn.cursor()

reasons = [
    ("ai_salah_baca", "AI Salah Baca Stand (Edit Angka)", 1, 1),
    ("meter_buram", "Foto Meter Buram / Tidak Terbaca", 1, 2),
    ("beda_id_pelanggan", "ID Pelanggan di Foto Berbeda", 1, 3),
    ("beda_merek", "Merek Meter di Foto Berbeda", 1, 4),
    ("anomali_wajar", "Anomali Wajar (Stand Sesuai)", 1, 5)
]

for val, lbl, active, sort in reasons:
    try:
        c.execute("INSERT INTO reason_options (value, label, is_active, sort_order) VALUES (?, ?, ?, ?)", (val, lbl, active, sort))
    except sqlite3.IntegrityError:
        pass # Udah ada

conn.commit()
print("Alasan (reasons) berhasil dikembalikan!")
