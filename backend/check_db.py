from dotenv import load_dotenv
import os
load_dotenv()

from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL")
print("URL Database aktif:", url)
print()

engine = create_engine(url)
with engine.connect() as conn:
    row = conn.execute(text("SELECT version()")).fetchone()
    print("Terhubung ke:", row[0])
    print()

    tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")).fetchall()
    print("Tabel yang ada di PostgreSQL:")
    for t in tables:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {t[0]}")).fetchone()[0]
        print(f"  - {t[0]}: {count} baris")
