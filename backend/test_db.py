import sqlalchemy
from sqlalchemy import create_engine
engine = create_engine('postgresql://admin_pln:RahasiaPassword123!@localhost:5432/pln_kwh')
with engine.connect() as conn:
    res = conn.execute(sqlalchemy.text("SELECT id, session_id, unit, kode_unit FROM verification_records WHERE id_pelanggan = '171200289992' LIMIT 1")).fetchone()
    print('Record:', res)
    if res:
        ses = conn.execute(sqlalchemy.text("SELECT id, kode_unit FROM upload_sessions WHERE id = " + str(res[1]))).fetchone()
        print('Session:', ses)
