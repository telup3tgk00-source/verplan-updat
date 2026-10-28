from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReasonOption, User, RoleEnum
from app.routers.auth import get_current_user
from app.permissions import CAN_MANAGE_REASONS
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

class ReasonCreate(BaseModel):
    value: str
    label: str
    sort_order: int = 0
    requires_stand_correction: bool = False

class ReasonOut(BaseModel):
    id: int
    value: str
    label: str
    is_active: bool
    sort_order: int
    requires_stand_correction: bool
    uid_code: Optional[str] = None
    class Config:
        from_attributes = True

@router.get("/reasons", response_model=List[ReasonOut])
def get_reasons(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(ReasonOption)
    if current_user.role != RoleEnum.super_admin:
        uid_code = current_user.kode_unit[:2] if current_user.kode_unit else '17'
        q = q.filter(ReasonOption.uid_code == uid_code)
    
    return q.order_by(ReasonOption.sort_order).all()

@router.post("/reasons", response_model=ReasonOut)
def create_reason(req: ReasonCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in CAN_MANAGE_REASONS:
        raise HTTPException(status_code=403, detail="Hanya UID dan Super Admin yang dapat menambah alasan")
        
    uid_code = current_user.kode_unit[:2] if current_user.kode_unit else '17'
    
    query_existing = db.query(ReasonOption).filter_by(value=req.value)
    if uid_code:
        query_existing = query_existing.filter_by(uid_code=uid_code)
        
    existing = query_existing.first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Key/value alasan sudah ada dan masih aktif")
        else:
            # Reaktivasi alasan yang sudah dihapus secara soft-delete
            conflict_q = db.query(ReasonOption).filter(
                ReasonOption.sort_order == req.sort_order, 
                ReasonOption.id != existing.id,
                ReasonOption.is_active == True
            )
            if uid_code:
                conflict_q = conflict_q.filter_by(uid_code=uid_code)
            
            conflict = conflict_q.first()
            if conflict:
                shift_q = db.query(ReasonOption).filter(
                    ReasonOption.sort_order >= req.sort_order,
                    ReasonOption.id != existing.id,
                    ReasonOption.is_active == True
                )
                if uid_code:
                    shift_q = shift_q.filter_by(uid_code=uid_code)
                shift_q.update({"sort_order": ReasonOption.sort_order + 1}, synchronize_session=False)
            
            existing.label = req.label
            existing.sort_order = req.sort_order
            existing.requires_stand_correction = req.requires_stand_correction
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

    # Auto-Shift untuk Alasan yang benar-benar baru
    conflict_q = db.query(ReasonOption).filter_by(sort_order=req.sort_order, is_active=True)
    if uid_code:
        conflict_q = conflict_q.filter_by(uid_code=uid_code)
        
    if conflict_q.first():
        shift_q = db.query(ReasonOption).filter(ReasonOption.sort_order >= req.sort_order, ReasonOption.is_active == True)
        if uid_code:
            shift_q = shift_q.filter_by(uid_code=uid_code)
        shift_q.update({"sort_order": ReasonOption.sort_order + 1}, synchronize_session=False)

    reason_data = req.model_dump()
    reason_data["uid_code"] = uid_code
    reason = ReasonOption(**reason_data)
    db.add(reason)
    db.commit()
    db.refresh(reason)
    return reason

@router.put("/reasons/{reason_id}", response_model=ReasonOut)
def update_reason(reason_id: int, req: ReasonCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in CAN_MANAGE_REASONS:
        raise HTTPException(status_code=403, detail="Hanya UID dan Super Admin yang dapat mengubah alasan")
        
    reason = db.query(ReasonOption).filter_by(id=reason_id).first()
    if not reason:
        raise HTTPException(status_code=404, detail="Alasan tidak ditemukan")
        
    uid_code = current_user.kode_unit[:2] if current_user.kode_unit else '17'
    if current_user.role != RoleEnum.super_admin and reason.uid_code != uid_code:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke alasan ini")

    # Auto-Shift untuk Update: Jika urutan diubah dan menabrak yang lain
    if req.sort_order != reason.sort_order:
        conflict_q = db.query(ReasonOption).filter(
            ReasonOption.sort_order == req.sort_order, 
            ReasonOption.id != reason_id,
            ReasonOption.is_active == True
        )
        if uid_code:
            conflict_q = conflict_q.filter_by(uid_code=uid_code)
            
        if conflict_q.first():
            shift_q = db.query(ReasonOption).filter(
                ReasonOption.sort_order >= req.sort_order, 
                ReasonOption.id != reason_id,
                ReasonOption.is_active == True
            )
            if uid_code:
                shift_q = shift_q.filter_by(uid_code=uid_code)
                
            shift_q.update({"sort_order": ReasonOption.sort_order + 1}, synchronize_session=False)

    reason.label = req.label
    reason.sort_order = req.sort_order
    reason.requires_stand_correction = req.requires_stand_correction
    db.commit()
    db.refresh(reason)
    return reason

@router.delete("/reasons/{reason_id}")
def delete_reason(reason_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in CAN_MANAGE_REASONS:
        raise HTTPException(status_code=403, detail="Hanya UID dan Super Admin yang dapat menghapus alasan")
        
    reason = db.query(ReasonOption).filter_by(id=reason_id).first()
    if not reason:
        raise HTTPException(status_code=404, detail="Alasan tidak ditemukan")
        
    uid_code = current_user.kode_unit[:2] if current_user.kode_unit else '17'
    if current_user.role != RoleEnum.super_admin and reason.uid_code != uid_code:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke alasan ini")
        
    reason.is_active = False
    db.commit()
    return {"message": "Alasan dinonaktifkan"}
