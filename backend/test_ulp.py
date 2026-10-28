import urllib.request
import json
import sqlalchemy
from sqlalchemy import create_engine
import jwt
from datetime import datetime, timedelta

engine = create_engine('postgresql://admin_pln:RahasiaPassword123!@localhost:5432/pln_kwh')
with engine.connect() as conn:
    user = conn.execute(sqlalchemy.text("SELECT id, username, kode_unit FROM users WHERE kode_unit = '17130' LIMIT 1")).fetchone()
    print('ULP User:', user)
    
    if user:
        SECRET_KEY = 'kunci-rahasia-production-pln-metrik'
        token = jwt.encode({'sub': user[1], 'exp': datetime.utcnow() + timedelta(days=1)}, SECRET_KEY, algorithm='HS256')
        
        req = urllib.request.Request('http://localhost:8000/api/upload/sessions', headers={'Authorization': 'Bearer ' + token})
        res = urllib.request.urlopen(req)
        data = json.loads(res.read())
        print('Total sessions returned:', len(data))
        for s in data:
            print(s['batch_name'], s['total_records'])
