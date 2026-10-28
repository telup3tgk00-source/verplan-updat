import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, records, upload, assignments, export, notifications, foto, settings, audit
from app import models

from sqlalchemy import text
from app.database import engine, Base, SessionLocal

# Buat semua tabel otomatis
Base.metadata.create_all(bind=engine)

# SQLite/PostgreSQL migration helper for new columns
# Guard flag: hanya jalankan sekali per proses (cegah double-run di multi-threaded gunicorn)
_migrations_done = False

def run_migrations():
    global _migrations_done
    if _migrations_done:
        return
    _migrations_done = True
    
    db = SessionLocal()
    try:
        # ── verification_records columns ──────────────────────────────
        for col_sql in [
            "ALTER TABLE verification_records ADD COLUMN IF NOT EXISTS record_type VARCHAR(10) DEFAULT 'beda'",
            "ALTER TABLE verification_records ADD COLUMN IF NOT EXISTS reason_type VARCHAR(50)",
            "ALTER TABLE verification_records ADD COLUMN IF NOT EXISTS corrected_stand FLOAT",
            "ALTER TABLE verification_records ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)",
        ]:
            try:
                db.execute(text(col_sql))
            except Exception:
                db.rollback()

        # ── upload_sessions columns ───────────────────────────────────
        for col_sql in [
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS file_match_name VARCHAR(200)",
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS file_beda_name VARCHAR(200)",
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS total_match INTEGER DEFAULT 0",
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS total_beda INTEGER DEFAULT 0",
            "ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)",
        ]:
            try:
                db.execute(text(col_sql))
            except Exception:
                db.rollback()

        # ── reason_options columns ────────────────────────────────────
        try:
            db.execute(text("ALTER TABLE reason_options ADD COLUMN IF NOT EXISTS requires_stand_correction BOOLEAN DEFAULT false"))
        except Exception:
            db.rollback()

        # ── users columns (kode_unit & parent_id) ─────────────────────
        for col_sql in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS kode_unit VARCHAR(20)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS parent_id INTEGER",
        ]:
            try:
                db.execute(text(col_sql))
            except Exception:
                db.rollback()

        # ── Indexing Migration ────────────────────────────────────────
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS ix_verification_records_status ON verification_records (status)",
            "CREATE INDEX IF NOT EXISTS ix_verification_records_assigned_to ON verification_records (assigned_to)",
            "CREATE INDEX IF NOT EXISTS ix_verification_records_is_anomaly ON verification_records (is_anomaly)",
            "CREATE INDEX IF NOT EXISTS ix_verification_records_is_deleted ON verification_records (is_deleted)"
        ]:
            try:
                db.execute(text(idx_sql))
            except Exception:
                db.rollback()

        # ── PostgreSQL: upgrade RoleEnum type dengan nilai baru ───────
        from app.database import engine as _engine
        if "postgresql" in str(_engine.url):
            for new_val in ["super_admin", "uid", "up3", "ulp"]:
                try:
                    db.execute(text(f"ALTER TYPE roleenum ADD VALUE IF NOT EXISTS '{new_val}'"))
                except Exception:
                    db.rollback()

        db.commit()
    finally:
        db.close()

run_migrations()


DEBUG = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="PLN KWH Verification API",
    description="Backend untuk sistem verifikasi meter PLN",
    version="1.1.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

# CORS agar React bisa akses
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"), 
    "http://127.0.0.1:5173",
    "https://portalapp.iconpln.co.id"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurasi Rate Limiting (Brute Force Protection)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Daftarkan semua router
app.include_router(auth.router,          prefix="/api/auth",          tags=["auth"])
app.include_router(users.router,         prefix="/api/users",         tags=["Users"])
app.include_router(records.router,       prefix="/api/records",       tags=["Records"])
app.include_router(upload.router,        prefix="/api/upload",        tags=["Upload"])
app.include_router(assignments.router,   prefix="/api/assignments",   tags=["Assignments"])
app.include_router(export.router,        prefix="/api/export",        tags=["Export"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(foto.router,          prefix="/api",               tags=["Foto Meter"])
app.include_router(settings.router,      prefix="/api/settings",      tags=["Settings"])
app.include_router(audit.router,         prefix="/api/audit",         tags=["Audit"])

@app.get("/")
def root():
    return {"message": "PLN KWH Verification API is running"}

from fastapi import Depends
from app.routers.auth import get_current_user
from app.models import User
import time

DASHBOARD_CACHE = {}
CACHE_TTL = 120  # 2 menit — cukup lama untuk 1.6M rows, cukup segar untuk operasional

def get_cache(key: str):
    if key in DASHBOARD_CACHE:
        data, timestamp = DASHBOARD_CACHE[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None

def set_cache(key: str, data):
    DASHBOARD_CACHE[key] = (data, time.time())

@app.get("/api/dashboard/stats")
def dashboard_stats(bulan: str = None, current_user: User = Depends(get_current_user)):
    cache_key = f"stats_{current_user.id}_{bulan}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models import VerificationRecord, StatusEnum, UploadSession, RoleEnum
        from app.permissions import apply_scope_filter
        
        # Base query for records
        query = db.query(VerificationRecord).filter(VerificationRecord.is_deleted == False)
        query = apply_scope_filter(query, VerificationRecord, current_user)
        
        # Filter jika user adalah verifikator, hanya tampilkan tugasnya sendiri
        if current_user.role == RoleEnum.verifikator:
            query = query.filter(VerificationRecord.assigned_to == current_user.id)
            
        if bulan:
            query = query.join(UploadSession, VerificationRecord.session_id == UploadSession.id)\
                         .filter(UploadSession.bulan_verifikasi == bulan)
                         
        # Lakukan 1 query agregasi untuk menghemat waktu (daripada 6 query .count() terpisah)
        from sqlalchemy import func, case
        agg_query = db.query(
            func.count(VerificationRecord.id).label('total'),
            func.sum(case((VerificationRecord.status == StatusEnum.PENDING, 1), else_=0)).label('pending'),
            func.sum(case((VerificationRecord.status == StatusEnum.VERIFIED_OK, 1), else_=0)).label('ok'),
            func.sum(case((VerificationRecord.status == StatusEnum.VERIFIED_REJECT, 1), else_=0)).label('reject'),
            func.sum(case((VerificationRecord.status == StatusEnum.NEED_INVESTIGATION, 1), else_=0)).label('inv'),
            func.sum(case((VerificationRecord.is_anomaly == True, 1), else_=0)).label('anomaly')
        )
        
        # Apply the exact same filters to the aggregation query
        agg_query = agg_query.filter(VerificationRecord.is_deleted == False)
        agg_query = apply_scope_filter(agg_query, VerificationRecord, current_user)
        if current_user.role == RoleEnum.verifikator:
            agg_query = agg_query.filter(VerificationRecord.assigned_to == current_user.id)
        if bulan:
            agg_query = agg_query.join(UploadSession, VerificationRecord.session_id == UploadSession.id)\
                                 .filter(UploadSession.bulan_verifikasi == bulan)
        
        agg_res = agg_query.first()
        total = agg_res.total or 0
        pending = agg_res.pending or 0
        ok = agg_res.ok or 0
        reject = agg_res.reject or 0
        inv = agg_res.inv or 0
        anomaly = agg_res.anomaly or 0
        
        pct = round((ok + reject + inv) / total * 100, 1) if total > 0 else 0
        
        # Data untuk chart: Progres per sesi — 1 query GROUP BY, bukan N×2 count()
        from sqlalchemy import func, case as sa_case
        session_query = db.query(UploadSession)
        session_query = apply_scope_filter(session_query, UploadSession, current_user)
        if bulan:
            session_query = session_query.filter(UploadSession.bulan_verifikasi == bulan)
        sessions = session_query.order_by(UploadSession.id.desc()).limit(5).all()
        session_ids = [s.id for s in sessions]
        
        chart_data = []
        if session_ids:
            # Single GROUP BY query untuk semua sesi sekaligus
            chart_base = db.query(
                VerificationRecord.session_id,
                func.count(VerificationRecord.id).label('s_total'),
                func.sum(sa_case((VerificationRecord.status != StatusEnum.PENDING, 1), else_=0)).label('s_done')
            ).filter(
                VerificationRecord.session_id.in_(session_ids),
                VerificationRecord.is_deleted == False
            )
            chart_base = apply_scope_filter(chart_base, VerificationRecord, current_user)
            if current_user.role == RoleEnum.verifikator:
                chart_base = chart_base.filter(VerificationRecord.assigned_to == current_user.id)
            chart_rows = {r.session_id: r for r in chart_base.group_by(VerificationRecord.session_id).all()}
            
            for i, s in enumerate(reversed(sessions)):
                r = chart_rows.get(s.id)
                if not r:
                    continue
                s_total = r.s_total or 0
                s_done = r.s_done or 0
                if current_user.role == RoleEnum.verifikator and s_total == 0:
                    continue
                chart_data.append({
                    "name": f"Sesi {i+1}",
                    "done": s_done,
                    "total": s_total,
                    "pct": round(s_done / s_total * 100, 1) if s_total > 0 else 0
                })

        result = {
            "total": total, "pending": pending, "verified_ok": ok,
            "verified_reject": reject, "need_investigation": inv, 
            "anomaly": anomaly, "progress_pct": pct,
            "chart_data": chart_data[::-1] # Reverse to chronological
        }
        set_cache(cache_key, result)
        return result
    finally:
        db.close()

@app.get("/api/dashboard/progress-ulp")
def progress_ulp(bulan: str = None, current_user: User = Depends(get_current_user)):
    cache_key = f"ulp_{current_user.id}_{bulan}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    from app.database import SessionLocal
    from sqlalchemy import func, case
    from app.models import VerificationRecord, StatusEnum, UploadSession, User as DBUser, RoleEnum
    from app.permissions import apply_scope_filter
    db = SessionLocal()
    try:
        q = db.query(
            VerificationRecord.kode_unit,
            func.count(VerificationRecord.id).label('total'),
            func.sum(case((VerificationRecord.status == StatusEnum.PENDING, 1), else_=0)).label('pending'),
            func.sum(case((VerificationRecord.status == StatusEnum.VERIFIED_OK, 1), else_=0)).label('ok'),
            func.sum(case((VerificationRecord.status == StatusEnum.VERIFIED_REJECT, 1), else_=0)).label('reject'),
            func.sum(case((VerificationRecord.status == StatusEnum.NEED_INVESTIGATION, 1), else_=0)).label('inv')
        ).filter(VerificationRecord.is_deleted == False)
        
        q = apply_scope_filter(q, VerificationRecord, current_user)
        
        if bulan:
            q = q.join(UploadSession, VerificationRecord.session_id == UploadSession.id)\
                 .filter(UploadSession.bulan_verifikasi == bulan)
                 
        grouped = q.group_by(VerificationRecord.kode_unit).all()
        
        result = []
        for row in grouped:
            # Cek ULP, kalau gak ada cek UP3 (untuk kasus 2 layer)
            user_unit = db.query(DBUser).filter(DBUser.kode_unit == row.kode_unit, DBUser.role.in_([RoleEnum.ulp, RoleEnum.up3])).first()
            ulp_name = user_unit.full_name if user_unit else f"Unit {row.kode_unit or 'N/A'}"
            
            total = row.total
            ok = row.ok or 0
            reject = row.reject or 0
            inv = row.inv or 0
            
            result.append({
                "kode_unit": row.kode_unit,
                "nama_ulp": ulp_name,
                "total": total,
                "pending": row.pending or 0,
                "verified_ok": ok,
                "verified_reject": reject,
                "need_investigation": inv,
                "progress_pct": round((ok + reject + inv) / total * 100, 1) if total > 0 else 0
            })
            
        # Urutkan berdasarkan unit
        final_result = sorted(result, key=lambda x: str(x['kode_unit']))
        set_cache(cache_key, final_result)
        return final_result
    finally:
        db.close()

@app.get("/api/dashboard/uid")
def dashboard_uid(bulan: str = None, current_user: User = Depends(get_current_user)):
    cache_key = f"uid_{current_user.id}_{bulan}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    from fastapi import HTTPException
    from app.database import SessionLocal
    from sqlalchemy import func, case
    from app.models import VerificationRecord, StatusEnum, UploadSession, User as DBUser, RoleEnum
    from datetime import datetime, timedelta

    if current_user.role not in [RoleEnum.uid, RoleEnum.super_admin, RoleEnum.up3]:
        raise HTTPException(status_code=403, detail="Hanya untuk role UID, Super Admin, atau UP3")

    db = SessionLocal()
    try:
        # 1. Leaderboard (UID untuk Super Admin, UP3 untuk UID, ULP untuk UP3)
        if current_user.role == RoleEnum.super_admin:
            target_role = RoleEnum.uid
        elif current_user.role == RoleEnum.uid:
            target_role = RoleEnum.up3
        else:
            target_role = RoleEnum.ulp
            
        sub_query = db.query(DBUser).filter(DBUser.role == target_role)
        if current_user.role != RoleEnum.super_admin:
            user_kode = current_user.kode_unit if current_user.kode_unit else '17'
            sub_query = sub_query.filter(DBUser.kode_unit.like(f"{user_kode}%"))
        sub_list = sub_query.all()
        
        # Lakukan 1 query GROUP BY untuk seluruh unit, lalu agregasi di Python
        agg_q = db.query(
            VerificationRecord.kode_unit,
            func.count(VerificationRecord.id).label('total'),
            func.sum(case((VerificationRecord.status != StatusEnum.PENDING, 1), else_=0)).label('done'),
            func.sum(case((VerificationRecord.is_anomaly == True, 1), else_=0)).label('anomaly')
        ).filter(VerificationRecord.is_deleted == False)
        
        if current_user.role != RoleEnum.super_admin:
            user_kode = current_user.kode_unit if current_user.kode_unit else '17'
            agg_q = agg_q.filter(VerificationRecord.kode_unit.like(f"{user_kode}%"))
            
        if bulan:
            agg_q = agg_q.join(UploadSession, VerificationRecord.session_id == UploadSession.id)\
                         .filter(UploadSession.bulan_verifikasi == bulan)
                         
        agg_q = agg_q.group_by(VerificationRecord.kode_unit)
        all_unit_stats = agg_q.all()
        
        leaderboard = []
        for sub in sub_list:
            total = 0
            done = 0
            anomaly = 0
            
            # Hitung dari memori Python yang prefix-nya cocok
            for st in all_unit_stats:
                if st.kode_unit and st.kode_unit.startswith(sub.kode_unit):
                    total += (st.total or 0)
                    done += (st.done or 0)
                    anomaly += (st.anomaly or 0)
            
            leaderboard.append({
                "kode_unit": sub.kode_unit,
                "nama_unit": sub.full_name,
                "total": total,
                "done": done,
                "anomaly": anomaly,
                "progress_pct": round((done / total * 100), 1) if total > 0 else 0
            })
            
        leaderboard = sorted(leaderboard, key=lambda x: x['progress_pct'], reverse=True)

        # 2. Daily Trend (7 hari terakhir dari data yang diverifikasi)
        # Menghindari db dependent date-truncation, kita ambil records verified >= 7 days ago, lalu agregasi di python
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        trend_query = db.query(VerificationRecord.verified_at).filter(
            VerificationRecord.is_deleted == False,
            VerificationRecord.status != StatusEnum.PENDING,
            VerificationRecord.verified_at >= seven_days_ago
        )
        if current_user.kode_unit and current_user.role != RoleEnum.super_admin:
            trend_query = trend_query.filter(VerificationRecord.kode_unit.like(f"{current_user.kode_unit}%"))
        if bulan:
            trend_query = trend_query.join(UploadSession).filter(UploadSession.bulan_verifikasi == bulan)
            
        verified_dates = [r[0] for r in trend_query.all() if r[0]]
        
        # Agregasi ke dict (YYYY-MM-DD -> count)
        date_counts = {}
        for i in range(7):
            d = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d")
            date_counts[d] = 0
            
        for vd in verified_dates:
            d_str = vd.strftime("%Y-%m-%d")
            if d_str in date_counts:
                date_counts[d_str] += 1
                
        daily_trend = [{"date": k, "count": v} for k, v in date_counts.items()]

        # 3. Anomaly Breakdown (Group by reason_type)
        anomaly_q = db.query(
            VerificationRecord.reason_type, 
            func.count(VerificationRecord.id).label('count')
        ).filter(
            VerificationRecord.is_deleted == False,
            VerificationRecord.is_anomaly == True,
            VerificationRecord.status != StatusEnum.PENDING
        )
        if current_user.kode_unit and current_user.role != RoleEnum.super_admin:
            anomaly_q = anomaly_q.filter(VerificationRecord.kode_unit.like(f"{current_user.kode_unit}%"))
        if bulan:
            anomaly_q = anomaly_q.join(UploadSession).filter(UploadSession.bulan_verifikasi == bulan)
            
        anomaly_breakdown = [
            {"reason": r.reason_type or "Lainnya", "count": r.count}
            for r in anomaly_q.group_by(VerificationRecord.reason_type).all()
        ]

        # 4. Bottleneck / Pending Lama
        # Cari sesi yang punya pending terbanyak / paling lama
        bottleneck_q = db.query(
            UploadSession.batch_name,
            UploadSession.created_at,
            func.sum(case((VerificationRecord.status == StatusEnum.PENDING, 1), else_=0)).label('pending_count')
        ).join(VerificationRecord, UploadSession.id == VerificationRecord.session_id)\
         .filter(VerificationRecord.is_deleted == False)\
         .group_by(UploadSession.id)
         
        if current_user.kode_unit and current_user.role != RoleEnum.super_admin:
            bottleneck_q = bottleneck_q.filter(VerificationRecord.kode_unit.like(f"{current_user.kode_unit}%"))
        if bulan:
            bottleneck_q = bottleneck_q.filter(UploadSession.bulan_verifikasi == bulan)
            
        # Ambil 5 batch dengan pending tertinggi dan dibuat lebih dari 1 hari lalu
        yesterday = datetime.utcnow() - timedelta(days=1)
        bottleneck_list = []
        for row in bottleneck_q.all():
            if row.pending_count > 0 and row.created_at < yesterday:
                days_pending = (datetime.utcnow() - row.created_at).days
                bottleneck_list.append({
                    "batch_name": row.batch_name,
                    "pending_count": row.pending_count,
                    "days_pending": days_pending,
                    "status": "Kritis" if days_pending > 3 else "Peringatan"
                })
        
        bottlenecks = sorted(bottleneck_list, key=lambda x: x['pending_count'], reverse=True)[:5]

        final_result = {
            "leaderboard": leaderboard,
            "daily_trend": daily_trend,
            "anomaly_breakdown": anomaly_breakdown,
            "bottlenecks": bottlenecks
        }
        set_cache(cache_key, final_result)
        return final_result
    finally:
        db.close()