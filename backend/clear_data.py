from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models import UploadSession, VerificationRecord, AssignmentBatch
from sqlalchemy import text

db = SessionLocal()
try:
    print("Menghapus assignment_batches...")
    db.query(AssignmentBatch).filter(AssignmentBatch.session_id == 9).delete(synchronize_session=False)
    
    print("Menghapus verification_records (ini mungkin butuh beberapa detik karena ada 300k baris)...")
    db.query(VerificationRecord).filter(VerificationRecord.session_id == 9).delete(synchronize_session=False)
    
    print("Menghapus upload_session...")
    db.query(UploadSession).filter(UploadSession.id == 9).delete(synchronize_session=False)
    
    db.commit()
    print("SELESAI! Data 300k berhasil dibersihkan.")
except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
