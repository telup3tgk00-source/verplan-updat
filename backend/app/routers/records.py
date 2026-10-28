from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import VerificationRecord, AuditLog, StatusEnum, User
from app.schemas import RecordOut, RecordUpdate
from typing import List, Optional
from datetime import datetime
import time

from app.routers.auth import get_current_user
from app.permissions import apply_scope_filter

# Cache untuk lbkb-options (jarang berubah, full-scan sangat mahal di 1.6M rows)
_LBKB_CACHE = {"data": None, "ts": 0}
_LBKB_TTL = 300  # 5 menit

router = APIRouter()

@router.get("/", response_model=List[RecordOut])
def get_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    session_id: Optional[int] = None,
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    record_type: Optional[str] = None,
    unit: Optional[str] = None,
    reason_type: Optional[str] = None,
    anomaly_only: bool = False,
    merek_mismatch: bool = False,
    lbkb: Optional[str] = None,
    min_selisih: Optional[int] = None,
    max_selisih: Optional[int] = None,
    skip: int = 0,
    limit: int = 50
):
    q = db.query(VerificationRecord).filter_by(is_deleted=False)
    q = apply_scope_filter(q, VerificationRecord, current_user)
    
    if session_id:
        q = q.filter(VerificationRecord.session_id == session_id)
    if status:
        q = q.filter(VerificationRecord.status == status)
    from app.models import RoleEnum
    if current_user.role == RoleEnum.verifikator:
        q = q.filter(VerificationRecord.assigned_to == current_user.id)
    elif assigned_to:
        q = q.filter(VerificationRecord.assigned_to == assigned_to)
    if search:
        q = q.filter(VerificationRecord.id_pelanggan.contains(search))
    if record_type:
        q = q.filter(VerificationRecord.record_type == record_type)
    if unit:
        q = q.filter(VerificationRecord.unit == unit)
    if reason_type:
        q = q.filter(VerificationRecord.reason_type == reason_type)
    if anomaly_only:
        q = q.filter(VerificationRecord.is_anomaly == True)
    if merek_mismatch:
        q = q.filter(VerificationRecord.merek_ai != VerificationRecord.merek_petugas)
    if lbkb:
        lbkb_list = [x.strip() for x in lbkb.split(",")]
        q = q.filter(VerificationRecord.lbkb.in_(lbkb_list))
    if min_selisih is not None:
        q = q.filter(VerificationRecord.selisih >= min_selisih)
    if max_selisih is not None:
        q = q.filter(VerificationRecord.selisih <= max_selisih)
    return q.offset(skip).limit(limit).all()

@router.get("/lbkb-options")
def get_lbkb_options(db: Session = Depends(get_db)):
    # Gunakan cache agar tidak full-scan setiap saat
    now = time.time()
    if _LBKB_CACHE["data"] is not None and (now - _LBKB_CACHE["ts"]) < _LBKB_TTL:
        return _LBKB_CACHE["data"]
    
    options = db.query(VerificationRecord.lbkb)\
                .filter(
                    VerificationRecord.lbkb.isnot(None), 
                    VerificationRecord.lbkb != "",
                    VerificationRecord.lbkb != "LBKB" # Abaikan jika ada header nyasar dari excel
                )\
                .distinct().all()
    result = {"options": sorted([opt[0] for opt in options])}
    _LBKB_CACHE["data"] = result
    _LBKB_CACHE["ts"] = now
    return result

@router.patch("/{record_id}", response_model=RecordOut)
def update_record(record_id: int, req: RecordUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    record = db.query(VerificationRecord).filter_by(id=record_id, is_deleted=False).first()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Record tidak ditemukan")

    # Simpan audit log
    log = AuditLog(
        record_id=record_id,
        user_id=current_user.id,
        action="update_status",
        old_status=record.status.value if record.status else None,
        new_status=req.status.value,
        catatan=req.catatan
    )
    db.add(log)

    record.status = req.status
    record.catatan = req.catatan
    record.reason_type = req.reason_type
    record.corrected_stand = req.corrected_stand
    record.verified_by = current_user.id
    record.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(record)

    # Trigger Notifikasi ke Admin/Supervisor jika ada penolakan atau investigasi
    if req.status in [StatusEnum.VERIFIED_REJECT, StatusEnum.NEED_INVESTIGATION]:
        from app.models import User, RoleEnum, Notification
        
        # 1. Format status agar bahasa manusia
        status_label = "Perlu Investigasi" if req.status == StatusEnum.NEED_INVESTIGATION else "Ditolak"
        
        # 2. Format catatan (hanya tampil jika tidak kosong)
        catatan_text = f" Catatan: {req.catatan}" if req.catatan and str(req.catatan).strip() else ""
        
        supervisors = db.query(User).filter(User.role.in_([RoleEnum.super_admin, RoleEnum.uid, RoleEnum.up3, RoleEnum.ulp])).all()
        
        for sup in supervisors:
            # 3. Filter Scope: Kirim hanya ke super_admin ATAU atasan yang wilayahnya menaungi record ini
            is_in_scope = False
            if sup.role == RoleEnum.super_admin:
                is_in_scope = True
            elif sup.kode_unit and record.kode_unit and record.kode_unit.startswith(sup.kode_unit):
                is_in_scope = True
                
            if is_in_scope:
                db.add(Notification(
                    user_id=sup.id,
                    title=f"Data {status_label}",
                    message=f"Verifikator {current_user.full_name} menandai ID {record.id_pelanggan} sebagai {status_label}.{catatan_text}"
                ))
        db.commit()

    return record

@router.get("/stats/summary")
def get_summary(session_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(VerificationRecord).filter_by(is_deleted=False)
    q = apply_scope_filter(q, VerificationRecord, current_user)
    
    if session_id:
        q = q.filter(VerificationRecord.session_id == session_id)
    total = q.count()
    pending = q.filter(VerificationRecord.status == StatusEnum.PENDING).count()
    ok = q.filter(VerificationRecord.status == StatusEnum.VERIFIED_OK).count()
    reject = q.filter(VerificationRecord.status == StatusEnum.VERIFIED_REJECT).count()
    inv = q.filter(VerificationRecord.status == StatusEnum.NEED_INVESTIGATION).count()
    return {
        "total": total, "pending": pending,
        "verified_ok": ok, "verified_reject": reject,
        "need_investigation": inv,
        "progress_pct": round((ok + reject + inv) / total * 100, 1) if total > 0 else 0
    }