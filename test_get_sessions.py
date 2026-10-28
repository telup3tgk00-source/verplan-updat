import os
import sys
# add backend dir to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.database import SessionLocal
from app.models import UploadSession, VerificationRecord, User, RoleEnum
from app.routers.upload import get_sessions

db = SessionLocal()
# Simulate a ULP user
user = db.query(User).filter(User.kode_unit == '17130').first()
if user:
    print(f"Testing for user {user.username} with role {user.role} and kode_unit {user.kode_unit}")
    
    # We call the function directly!
    # Wait, the function needs Depends(). We can just pass the instances.
    res = get_sessions(db=db, current_user=user)
    print("Found", len(res), "sessions:")
    for s in res:
        print(s['batch_name'], s['total_records'])
else:
    print("User not found.")
