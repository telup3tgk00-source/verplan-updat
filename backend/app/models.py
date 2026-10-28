from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class RoleEnum(str, enum.Enum):
    super_admin = "super_admin"
    uid         = "uid"
    up3         = "up3"
    ulp         = "ulp"
    verifikator = "verifikator"

class StatusEnum(str, enum.Enum):
    PENDING             = "PENDING"
    VERIFIED_OK         = "VERIFIED_OK"
    VERIFIED_REJECT     = "VERIFIED_REJECT"
    NEED_INVESTIGATION  = "NEED_INVESTIGATION"

class ReasonOption(Base):
    __tablename__ = "reason_options"
    id                       = Column(Integer, primary_key=True, index=True)
    value                    = Column(String(100), index=True)  # Tidak unique secara global lagi
    label                    = Column(String(200))
    is_active                = Column(Boolean, default=True)
    sort_order               = Column(Integer, default=0)
    requires_stand_correction = Column(Boolean, default=False)
    uid_code                 = Column(String(10), nullable=True, index=True)  # Penanda kepemilikan provinsi (contoh: '17', '53')

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, index=True, nullable=False)
    password_hash   = Column(Text, nullable=False)
    full_name       = Column(String(100))
    role            = Column(Enum(RoleEnum), default=RoleEnum.verifikator)
    # kode unit PLN: UID=17, UP3=171, ULP=17100 — dipakai untuk scoping data
    kode_unit       = Column(String(20), nullable=True, index=True)
    # siapa yang membuat user ini (hierarki)
    parent_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    unit_penugasan  = Column(String(200), nullable=True)   # legacy, tetap disimpan
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

class UploadSession(Base):
    __tablename__ = "upload_sessions"
    id                 = Column(Integer, primary_key=True, index=True)
    uploaded_by        = Column(Integer, ForeignKey("users.id"))
    batch_name         = Column(String(200), nullable=True)
    bulan_verifikasi   = Column(String(6), nullable=True)
    file_match_name    = Column(String(200), nullable=True)
    file_beda_name     = Column(String(200), nullable=True)
    file_ai_name       = Column(String(200), nullable=True)
    file_petugas_name  = Column(String(200), nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    status             = Column(String(50), default="processing")
    total_records      = Column(Integer, default=0)
    total_match        = Column(Integer, default=0)
    total_beda         = Column(Integer, default=0)
    # kode unit UP3 yang upload — untuk scoping data
    kode_unit          = Column(String(20), nullable=True, index=True)
    records            = relationship("VerificationRecord", back_populates="session")

class VerificationRecord(Base):
    __tablename__ = "verification_records"
    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(Integer, ForeignKey("upload_sessions.id"), index=True)
    id_pelanggan    = Column(String(50), index=True)
    unit            = Column(String(50), nullable=True)
    kode_nama_biller = Column(String(200), nullable=True)
    record_type     = Column(String(10), default="beda")
    stand_ai        = Column(Float, nullable=True)
    stand_petugas   = Column(Float, nullable=True)
    selisih         = Column(Float, nullable=True)
    merek_ai        = Column(String(100), nullable=True)
    merek_petugas   = Column(String(100), nullable=True)
    tipe_ai         = Column(String(50), nullable=True)
    tipe_petugas    = Column(String(50), nullable=True)
    status          = Column(Enum(StatusEnum), default=StatusEnum.PENDING, index=True)
    assigned_to     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    catatan         = Column(Text, nullable=True)
    reason_type     = Column(String(50), nullable=True)
    corrected_stand = Column(Float, nullable=True)
    verified_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at     = Column(DateTime, nullable=True)
    is_anomaly      = Column(Boolean, default=False, index=True)
    is_deleted      = Column(Boolean, default=False, index=True)
    # kode unit untuk scoping (diisi dari sesi upload)
    kode_unit       = Column(String(20), nullable=True, index=True)
    lbkb            = Column(String(200), nullable=True)
    session         = relationship("UploadSession", back_populates="records")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id          = Column(Integer, primary_key=True, index=True)
    record_id   = Column(Integer, ForeignKey("verification_records.id"), index=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    action      = Column(String(100))
    old_status  = Column(String(50), nullable=True)
    new_status  = Column(String(50), nullable=True)
    catatan     = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

class AssignmentBatch(Base):
    __tablename__ = "assignment_batches"
    id             = Column(Integer, primary_key=True, index=True)
    session_id     = Column(Integer, ForeignKey("upload_sessions.id"), index=True)
    operator_id    = Column(Integer, ForeignKey("users.id"))
    total_assigned = Column(Integer, default=0)
    selesai        = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    title      = Column(String(200))
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)