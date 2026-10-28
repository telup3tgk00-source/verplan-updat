from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import VerificationRecord, AssignmentBatch, StatusEnum, User, RoleEnum
from app.schemas import AssignmentRequest
from app.routers.auth import get_current_user
from app.permissions import CAN_ASSIGN, apply_scope_filter

router = APIRouter()

@router.post("/")
def assign_tasks(req: AssignmentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in CAN_ASSIGN:
        raise HTTPException(status_code=403, detail="Hanya ULP dan Super Admin yang dapat membagi tugas")

    # 0. Hapus AssignmentBatch lama untuk sesi dan scope ini agar tidak menumpuk
    from app.models import User
    from sqlalchemy import or_
    ulp_operators = db.query(User.id).filter(
        or_(
            User.kode_unit.like(f"{current_user.kode_unit}%") if current_user.kode_unit else False,
            User.parent_id == current_user.id
        )
    ).all()
    op_ids = [u.id for u in ulp_operators]
    
    if op_ids:
        db.query(AssignmentBatch).filter(
            AssignmentBatch.session_id == req.session_id,
            AssignmentBatch.operator_id.in_(op_ids)
        ).delete(synchronize_session=False)
    db.commit()

    # 1. Reset semua assigned_to ke None agar bisa di-reassign bersih (Hanya scope user)
    reset_q = db.query(VerificationRecord).filter_by(
        session_id=req.session_id,
        is_deleted=False,
        record_type="beda"
    )
    reset_q = apply_scope_filter(reset_q, VerificationRecord, current_user)
    reset_q.update({"assigned_to": None}, synchronize_session=False)
    db.commit()

    # 2. Ambil record yang belum diassign
    query = db.query(VerificationRecord).filter_by(
        session_id=req.session_id,
        is_deleted=False,
        assigned_to=None,
        record_type="beda"
    )
    query = apply_scope_filter(query, VerificationRecord, current_user)

    # 2. Filter berdasarkan metode
    if req.method == "range":
        if not req.range_start or not req.range_end:
            raise HTTPException(status_code=400, detail="Range start dan end wajib diisi")
        query = query.filter(VerificationRecord.id_pelanggan.between(req.range_start, req.range_end))
    elif req.method == "prefix":
        if not req.prefix:
            raise HTTPException(status_code=400, detail="Prefix wajib diisi")
        query = query.filter(VerificationRecord.id_pelanggan.like(f"{req.prefix}%"))

    records = query.all()

    if not records:
        raise HTTPException(status_code=400, detail="Tidak ada record yang sesuai kriteria/belum diassign")

    n_ops = len(req.operator_ids)
    if n_ops == 0:
        raise HTTPException(status_code=400, detail="Pilih minimal 1 verifikator")

    # 3. Bagi tugas
    # Jika manual/range/prefix dan hanya 1 operator, assign semua ke dia
    # Jika auto, bagi rata ke semua operator_ids
    batches = []
    if req.method == "auto" or (len(records) > 0 and n_ops > 1):
        chunk = len(records) // n_ops
        for i, op_id in enumerate(req.operator_ids):
            start = i * chunk
            end = start + chunk if i < n_ops - 1 else len(records)
            batch_records = records[start:end]
            
            for rec in batch_records:
                rec.assigned_to = op_id
            
            if batch_records:
                batch = AssignmentBatch(
                    session_id=req.session_id,
                    operator_id=op_id,
                    total_assigned=len(batch_records)
                )
                db.add(batch)
                batches.append({"operator_id": op_id, "total": len(batch_records)})
    else:
        # Assign semua ke operator pertama (untuk manual/range/prefix yang spesifik 1 orang)
        op_id = req.operator_ids[0]
        for rec in records:
            rec.assigned_to = op_id
        
        batch = AssignmentBatch(
            session_id=req.session_id,
            operator_id=op_id,
            total_assigned=len(records)
        )
        db.add(batch)
        batches.append({"operator_id": op_id, "total": len(records)})

    db.commit()
    
    # 4. Buat notifikasi
    from app.models import Notification
    for b in batches:
        notif = Notification(
            user_id=b["operator_id"],
            title="Tugas Baru Assigned",
            message=f"Anda menerima {b['total']} data baru untuk diverifikasi pada Sesi #{req.session_id}."
        )
        db.add(notif)
    db.commit()

    assigned_count = sum(b['total'] for b in batches)
    return {"message": f"Tugas berhasil dibagi ke {len(batches)} petugas.", "distribution": batches, "total_processed": assigned_count}

@router.get("/progress")
def get_progress(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models import User
    from sqlalchemy import func

    # Ambil set user_id yang masih ada di DB dan sesuai scope (agar ULP A tidak melihat tugas ULP B)
    from sqlalchemy import or_
    q_users = db.query(User.id)
    if current_user.kode_unit:
        q_users = q_users.filter(
            or_(
                User.kode_unit.like(f"{current_user.kode_unit}%"),
                User.parent_id == current_user.id
            )
        )
    existing_user_ids = {u.id for u in q_users.all()}

    batches = db.query(AssignmentBatch).filter_by(session_id=session_id).all()

    # Deduplikasi per operator_id — ambil yang total_assigned terbesar
    seen = {}
    for b in batches:
        # Skip ghost user (sudah dihapus)
        if b.operator_id not in existing_user_ids:
            continue
        if b.operator_id not in seen or b.total_assigned > seen[b.operator_id].total_assigned:
            seen[b.operator_id] = b

    result = []
    for b in seen.values():
        selesai = db.query(VerificationRecord).filter(
            VerificationRecord.session_id == session_id,
            VerificationRecord.assigned_to == b.operator_id,
            VerificationRecord.status != StatusEnum.PENDING
        ).count()
        result.append({
            "operator_id": b.operator_id,
            "total_assigned": b.total_assigned,
            "selesai": selesai,
            "pct": round(selesai / b.total_assigned * 100, 1) if b.total_assigned > 0 else 0
        })
    return result