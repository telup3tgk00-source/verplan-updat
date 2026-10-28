from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models import RoleEnum, StatusEnum

# ── AUTH ──────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    kode_unit: Optional[str] = None

# ── USER ──────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: RoleEnum = RoleEnum.verifikator
    kode_unit: Optional[str] = None
    unit_penugasan: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: RoleEnum
    kode_unit: Optional[str] = None
    unit_penugasan: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ── RECORD ────────────────────────────────────────
class RecordOut(BaseModel):
    id: int
    session_id: int
    id_pelanggan: str
    unit: Optional[str]
    kode_nama_biller: Optional[str]
    record_type: Optional[str] = "beda"
    stand_ai: Optional[float]
    stand_petugas: Optional[float]
    selisih: Optional[float]
    merek_ai: Optional[str]
    merek_petugas: Optional[str]
    tipe_ai: Optional[str]
    tipe_petugas: Optional[str]
    status: StatusEnum
    assigned_to: Optional[int]
    catatan: Optional[str]
    reason_type: Optional[str]
    corrected_stand: Optional[float]
    verified_at: Optional[datetime]
    is_anomaly: bool
    kode_unit: Optional[str] = None
    lbkb: Optional[str] = None

    class Config:
        from_attributes = True

class RecordUpdate(BaseModel):
    status: StatusEnum
    catatan: Optional[str] = None
    reason_type: Optional[str] = None
    corrected_stand: Optional[float] = None

# ── ASSIGNMENT ────────────────────────────────────
class AssignmentRequest(BaseModel):
    session_id: int
    method: str = "auto"
    operator_ids: list[int]
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    prefix: Optional[str] = None

# ── DASHBOARD ─────────────────────────────────────
class DashboardStats(BaseModel):
    total: int
    pending: int
    verified_ok: int
    verified_reject: int
    need_investigation: int
    progress_pct: float