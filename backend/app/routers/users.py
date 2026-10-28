from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, RoleEnum
from app.schemas import UserCreate, UserOut
from app.permissions import can_create_role, validate_kode_unit_hierarchy, ADMIN_ROLES
from passlib.context import CryptContext
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from app.routers.auth import get_current_user


@router.get("/", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Super admin: lihat semua user.
    UID/UP3/ULP: hanya lihat user yang mereka buat (parent_id = current_user.id)
                 atau user dalam scope kode_unit mereka.
    """
    if current_user.role == RoleEnum.super_admin:
        return db.query(User).order_by(User.created_at.desc()).all()

    # Untuk role lain: tampilkan user yang dibuat oleh user ini, atau yang kode_unit-nya di bawah mereka
    query = db.query(User)
    if current_user.kode_unit:
        query = query.filter(
            (User.kode_unit.like(f"{current_user.kode_unit}%")) |
            (User.parent_id == current_user.id)
        )
    else:
        query = query.filter(User.parent_id == current_user.id)
    return query.order_by(User.created_at.desc()).all()


@router.post("/", response_model=UserOut)
def create_user(req: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Pastikan role pembuat bisa membuat role yang diminta
    if not can_create_role(current_user, req.role):
        raise HTTPException(
            status_code=403,
            detail=f"Role {current_user.role.value} tidak bisa membuat user dengan role {req.role.value}"
        )

    # Validasi kode_unit hierarki
    if not validate_kode_unit_hierarchy(current_user, req.kode_unit):
        raise HTTPException(
            status_code=400,
            detail=f"Kode unit harus diawali dengan kode unit Anda ({current_user.kode_unit})"
        )

    existing = db.query(User).filter_by(username=req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah digunakan")

    user = User(
        username=req.username,
        password_hash=pwd_context.hash(req.password),
        full_name=req.full_name,
        role=req.role,
        kode_unit=req.kode_unit,
        unit_penugasan=req.unit_penugasan,
        parent_id=current_user.id,  # catat siapa yang membuat
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.is_active = not user.is_active
    db.commit()
    return {"message": "Status diperbarui", "is_active": user.is_active}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="User admin utama tidak dapat dihapus")
        
    from app.models import Notification, AssignmentBatch, VerificationRecord, UploadSession, AuditLog
    
    # Cek apakah user punya history verifikasi atau upload (jika ya, tolak penghapusan fisik)
    has_history = db.query(VerificationRecord).filter(
        (VerificationRecord.assigned_to == user_id) | 
        (VerificationRecord.verified_by == user_id)
    ).first()
    has_uploads = db.query(UploadSession).filter_by(uploaded_by=user_id).first()
    
    if has_history or has_uploads:
        raise HTTPException(
            status_code=400, 
            detail="User ini sudah memiliki histori kerja (verifikasi/upload). Tidak dapat dihapus secara permanen, silakan gunakan fitur Nonaktifkan (Toggle Status)."
        )

    # Bersihkan relasi yang aman dihapus jika user belum bekerja
    db.query(Notification).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(AssignmentBatch).filter_by(operator_id=user_id).delete(synchronize_session=False)
    db.query(AuditLog).filter_by(user_id=user_id).delete(synchronize_session=False)
    
    db.delete(user)
    db.commit()
    return {"message": "User berhasil dihapus"}


class PasswordReset(BaseModel):
    new_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    kode_unit: Optional[str] = None
    unit_penugasan: Optional[str] = None


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.role is not None:
        user.role = req.role
    if req.kode_unit is not None:
        user.kode_unit = req.kode_unit
    if req.unit_penugasan is not None:
        user.unit_penugasan = req.unit_penugasan
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/password")
def reset_password(user_id: int, req: PasswordReset, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses ditolak")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.password_hash = pwd_context.hash(req.new_password)
    db.commit()
    return {"message": "Password berhasil diubah"}