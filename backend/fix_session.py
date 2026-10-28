from dotenv import load_dotenv
load_dotenv()
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("UPDATE upload_sessions SET kode_unit = '171' WHERE id = 9"))
    conn.execute(text("UPDATE verification_records SET kode_unit = '171' WHERE session_id = 9"))
    conn.commit()
    print("Updated session 9 to kode_unit 171")
