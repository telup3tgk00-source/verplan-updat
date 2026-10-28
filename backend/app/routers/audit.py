from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import AuditLog, User, VerificationRecord, RoleEnum, UploadSession
from app.routers.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_audit_logs(
    bulan: str = None,
    search: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.super_admin:
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang dapat melihat Audit Trail")

    q = db.query(AuditLog, User, VerificationRecord, UploadSession)\
          .join(User, AuditLog.user_id == User.id)\
          .join(VerificationRecord, AuditLog.record_id == VerificationRecord.id)\
          .join(UploadSession, VerificationRecord.session_id == UploadSession.id)

    if bulan:
        q = q.filter(UploadSession.bulan_verifikasi == bulan)
    if search:
        q = q.filter(VerificationRecord.id_pelanggan.contains(search))

    total = q.count()
    
    logs = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

    result = []
    for log, user, record, session in logs:
        result.append({
            "id": log.id,
            "record_id": log.record_id,
            "id_pelanggan": record.id_pelanggan,
            "user_name": user.full_name,
            "user_kode": user.kode_unit,
            "action": log.action,
            "old_status": log.old_status,
            "new_status": log.new_status,
            "catatan": log.catatan,
            "created_at": log.created_at,
            "bulan": session.bulan_verifikasi
        })

    return {
        "data": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }
