from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, User
from app.routers.auth import get_current_user
from pydantic import BaseModel
from typing import List
from datetime import datetime
import time

router = APIRouter()

# Cache per-user untuk unread-count agar tidak dipanggil ratusan kali per menit
# Dipanggil setiap ~5 detik per user, jadi 10 detik TTL mengurangi beban 50%
_UNREAD_CACHE: dict = {}
_UNREAD_TTL = 10  # detik

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True

@router.get("/", response_model=List[NotificationOut])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Invalidasi cache saat user membuka notifikasi lengkap
    _UNREAD_CACHE.pop(current_user.id, None)
    return db.query(Notification).filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(20).all()

@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter_by(id=notif_id, user_id=current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")
    notif.is_read = True
    db.commit()
    # Invalidasi cache saat ada perubahan
    _UNREAD_CACHE.pop(current_user.id, None)
    return {"message": "Success"}

@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = time.time()
    cached = _UNREAD_CACHE.get(current_user.id)
    if cached and (now - cached["ts"]) < _UNREAD_TTL:
        return {"count": cached["count"]}
    
    count = db.query(Notification).filter_by(user_id=current_user.id, is_read=False).count()
    _UNREAD_CACHE[current_user.id] = {"count": count, "ts": now}
    return {"count": count}
