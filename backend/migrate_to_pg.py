import os
import sys
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

# Tambahkan direktori backend ke sys.path agar bisa import modul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base
from app import models
from dotenv import load_dotenv

load_dotenv() # Load variables from .env

# URL Database
SQLITE_URL = "sqlite:///./pln_kwh.db"

# Gunakan DATABASE_URL dari .env jika ada, atau fallback
env_db_url = os.getenv("DATABASE_URL")
if env_db_url and "postgresql" in env_db_url:
    PG_URL = env_db_url
else:
    PG_URL = "postgresql://postgres:yoga@localhost:5432/metrik_db"

def migrate():
    print("=" * 50)
    print("Memulai Migrasi dari SQLite ke PostgreSQL...")
    print("=" * 50)

    print("1. Menghubungkan ke database...")
    try:
        sqlite_engine = create_engine(SQLITE_URL)
        pg_engine = create_engine(PG_URL)
        # Tes koneksi PostgreSQL
        with pg_engine.connect() as conn:
            pass
    except Exception as e:
        print(f"[X] Gagal terhubung ke database. Pastikan PostgreSQL sudah menyala dan URL benar.")
        print(f"Error: {e}")
        return

    print("2. Membuat skema tabel di PostgreSQL...")
    # Ini akan membuat semua tabel berdasarkan struktur models.py
    Base.metadata.create_all(bind=pg_engine)

    # Urutkan tabel agar foreign key tidak error (tabel parent diproses duluan)
    sorted_tables = Base.metadata.sorted_tables

    print("3. Memindahkan data...")
    with sqlite_engine.connect() as sqlite_conn:
        with pg_engine.connect() as pg_conn:
            # Matikan pengecekan Foreign Key di PostgreSQL agar data yatim piatu (orphaned) dari SQLite tetap bisa masuk
            pg_conn.execute(text("SET session_replication_role = 'replica';"))
            pg_conn.commit()

            try:
                # Opsional: Kosongkan tabel di PostgreSQL jika ada isinya
                # Kita lakukan secara terbalik (child duluan) agar aman dari constraint
                for table in reversed(sorted_tables):
                    pg_conn.execute(table.delete())
                    pg_conn.commit()

                # Tabel yang di-skip (data dummy/besar, tidak perlu dipindah)
                SKIP_TABLES = {"verification_records", "audit_logs"}

                # Mulai memindahkan data
                for table in sorted_tables:
                    if table.name in SKIP_TABLES:
                        print(f"   [SKIP] Tabel: {table.name} (dikecualikan)")
                        continue
                    print(f"   [ ] Migrasi tabel: {table.name}...", end=" ", flush=True)
                
                    rows = sqlite_conn.execute(table.select()).fetchall()
                    if not rows:
                        print(f"Kosong.")
                        continue
                    
                    # Ubah Row object ke dictionary
                    dicts = [dict(row._mapping) for row in rows]
                    
                    # Bulk insert ke PostgreSQL
                    pg_conn.execute(table.insert(), dicts)
                    pg_conn.commit()
                    
                    # Perbarui Auto Increment Sequence di PostgreSQL
                    try:
                        # Ini krusial agar insert data baru setelah migrasi tidak bentrok ID-nya
                        sql = text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table.name};")
                        pg_conn.execute(sql)
                        pg_conn.commit()
                    except Exception as e:
                        # Abaikan jika tabel tidak punya kolom 'id' / sequence
                        pass
                    
                    print(f"Sukses memindahkan {len(dicts)} baris.")

            finally:
                # Nyalakan kembali pengecekan Foreign Key
                pg_conn.execute(text("SET session_replication_role = 'origin';"))
                pg_conn.commit()

    print("=" * 50)
    print("[OK] MIGRASI SELESAI DENGAN SUKSES!")
    print("Silakan pastikan baris berikut ada di file .env:")
    print(f"DATABASE_URL={PG_URL}")
    print("=" * 50)

if __name__ == "__main__":
    migrate()
