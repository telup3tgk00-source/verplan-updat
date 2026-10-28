import sys
import os

# Deteksi lokasi: apakah dijalankan dari root (ada folder 'backend') atau dari dalam docker/backend
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(base_dir, "backend", "app")):
    sys.path.insert(0, os.path.join(base_dir, "backend"))
else:
    sys.path.insert(0, base_dir)

try:
    from app.database import engine
    from sqlalchemy import text
except ImportError:
    print("Gagal import modul. Pastikan script ini dijalankan di dalam virtual environment backend.")
    sys.exit(1)

def main():
    print("Memulai proses migrasi database untuk isolasi Alasan Perbedaan per-UID...")
    
    try:
        # Gunakan AUTOCOMMIT agar jika salah satu gagal (misal constraint tidak ada), 
        # operasi lain (seperti tambah kolom) tidak ikut ter-rollback (dibatalkan) oleh Postgres.
        with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
            # 1. Tambahkan kolom uid_code (dengan default '17' agar data lama otomatis jadi milik Lampung)
            try:
                print("1. Menambahkan kolom 'uid_code' dengan default '17'...")
                conn.execute(text("ALTER TABLE reason_options ADD COLUMN uid_code VARCHAR(10) DEFAULT '17'"))
                print("   [OK] Kolom berhasil ditambahkan.")
            except Exception as e:
                print(f"   [SKIP] Kolom mungkin sudah ada. Pesan: {str(e)}")

            # 2. Hapus Unique Constraint dari kolom 'value'
            print("2. Mencabut aturan UNIQUE pada kolom 'value'...")
            
            # Coba drop constraint untuk Postgres
            try:
                conn.execute(text("ALTER TABLE reason_options DROP CONSTRAINT reason_options_value_key"))
                print("   [OK] Constraint 'reason_options_value_key' dihapus.")
            except Exception:
                pass
                
            # Coba drop index unique untuk SQLite / Postgres fallback
            try:
                conn.execute(text("DROP INDEX IF EXISTS ix_reason_options_value"))
                print("   [OK] Index 'ix_reason_options_value' dihapus.")
            except Exception:
                pass
            
        print("\nMigrasi berhasil diselesaikan! Semua alasan lama kini aman milik UID 17 (Lampung).")
        print("Anda sekarang dapat membuat alasan dengan key yang sama di UID lain.")
        
    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan fatal: {e}")

if __name__ == "__main__":
    main()
