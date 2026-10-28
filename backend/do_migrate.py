from dotenv import load_dotenv
load_dotenv()
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Menambah kolom...")
    # 1. Tambah kolom baru
    for sql in [
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS parent_id INTEGER',
        'ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)',
        'ALTER TABLE verification_records ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)',
    ]:
        try:
            conn.execute(text(sql))
            conn.commit()
            print("OK:", sql)
        except Exception as e:
            conn.rollback()
            print("Skip:", str(e)[:100])

    print("Menambah ENUM...")
    # 2. Tambah nilai enum baru
    for val in ['super_admin', 'uid', 'up3', 'ulp']:
        try:
            # Karena PostgreSQL enum tidak punya IF NOT EXISTS yang support di dalam blok transaksi biasa di versi lama, 
            # kita pakai auto commit atau abaikan errornya
            conn.execute(text("COMMIT"))
            conn.execute(text(f"ALTER TYPE roleenum ADD VALUE '{val}'"))
            print("Added enum:", val)
        except Exception as e:
            conn.rollback()
            print("Enum sudah ada atau error:", val)

    print("Update Role Lama...")
    # 3. Update role lama ke super_admin
    try:
        conn.execute(text("UPDATE users SET role = 'super_admin' WHERE role::text NOT IN ('super_admin','uid','up3','ulp','verifikator')"))
        conn.commit()
        print("Role admin lama berhasil diubah ke super_admin")
    except Exception as e:
        conn.rollback()
        print("Update role error:", str(e))

print("DONE")
