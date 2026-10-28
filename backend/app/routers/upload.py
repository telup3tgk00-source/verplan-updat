from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_user
from app.models import UploadSession, VerificationRecord, StatusEnum, User, RoleEnum
from app.permissions import CAN_UPLOAD, apply_scope_filter
import pandas as pd
import io

router = APIRouter()

ANOMALY_THRESHOLD = 500

# ── Kolom yang dikenali dari file Excel Web 1 ───────────────────────────────
def find_col(df, candidates):
    """Cari nama kolom dari daftar alias (case-insensitive)."""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for name in candidates:
        if name.lower() in cols_lower:
            return cols_lower[name.lower()]
    return None

def safe_float(val):
    try:
        if pd.isna(val) or val == "":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def parse_excel_file(file_bytes: bytes, record_type: str, session_id: int, kode_unit: str = None) -> list:
    """
    Parse file Excel (MATCH atau BEDA) dari Web 1 dan kembalikan list VerificationRecord.
    Kolom yang dikenali: No, Waktu, ID Pelanggan, Stand AI, Stand Biller,
                         Selisih, Hasil Verifikasi, Merek, Tipe Stan, Batch, Nama Biller
    """
    df = pd.read_excel(io.BytesIO(file_bytes))

    # Normalisasi nama kolom
    df.columns = [str(c).strip() for c in df.columns]

    # Deteksi kolom
    col_id     = find_col(df, ["ID Pelanggan", "id_pelanggan", "IDPEL", "No Pelanggan"])
    col_stand_ai   = find_col(df, ["Stand AI", "stand_ai", "STAND AI", "KWH AI"])
    col_stand_bil  = find_col(df, ["Stand Biller", "stand_biller", "STAND BILLER", "Stand Petugas", "stand_baca"])
    col_selisih    = find_col(df, ["Selisih", "selisih", "SELISIH", "Diff"])
    col_merek      = find_col(df, ["Merek", "merek", "MEREK", "Merk"])
    col_tipe       = find_col(df, ["Tipe Stan", "tipe_stan", "TIPE STAN", "Tipe"])
    col_nama_bil   = find_col(df, ["Nama Biller", "nama_biller", "NAMA BILLER"])
    col_unit       = find_col(df, ["UNITUP", "Unit UP", "Unitup", "Unit", "unit", "UNIT"])
    col_unitap     = find_col(df, ["UNITAP", "Unit AP", "Unitap"])
    col_kode_nama_bil = find_col(df, ["Kode Nama Biller", "kode_nama_biller", "KODE NAMA BILLER"])
    col_lbkb          = find_col(df, ["LBKB", "lbkb"])

    if not col_id:
        raise ValueError("Kolom 'ID Pelanggan' tidak ditemukan di file Excel")

    records = []
    for _, row in df.iterrows():
        try:
            id_pel = str(row[col_id]).strip() if col_id else ""
            if not id_pel or id_pel.lower() in ("nan", "none", ""):
                continue

            stand_ai  = safe_float(row[col_stand_ai])  if col_stand_ai else None
            stand_bil = safe_float(row[col_stand_bil]) if col_stand_bil else None
            selisih   = safe_float(row[col_selisih])   if col_selisih else None

            # Hitung selisih jika tidak ada kolom
            if selisih is None and stand_ai is not None and stand_bil is not None:
                selisih = abs(stand_ai - stand_bil)

            merek     = str(row[col_merek]).strip()    if col_merek    and pd.notna(row[col_merek])    else None
            tipe      = str(row[col_tipe]).strip()     if col_tipe     and pd.notna(row[col_tipe])     else None
            nama_bil  = str(row[col_nama_bil]).strip() if col_nama_bil and pd.notna(row[col_nama_bil]) else None
            unit      = str(row[col_unit]).strip()     if col_unit     and pd.notna(row[col_unit])     else None
            unitap    = str(row[col_unitap]).strip()   if col_unitap   and pd.notna(row[col_unitap])   else None
            kode_nama_biller = str(row[col_kode_nama_bil]).strip() if col_kode_nama_bil and pd.notna(row[col_kode_nama_bil]) else None
            lbkb      = str(row[col_lbkb]).strip()     if col_lbkb     and pd.notna(row[col_lbkb])     else None

            # LOGIKA PENENTUAN KODE UNIT (MENDUKUNG FORMAT ANGKA & FORMAT HIERARKI BEDA HURUF)
            final_kode_unit = unit if unit else kode_unit
            
            # Jika excel punya UNITAP, pakai UNITAP. Jika tidak, otomatis warisi kode uploader (kode_unit)
            bapak_kode = unitap if unitap else kode_unit
            
            if bapak_kode and unit:
                # Jika unit (misal: 53701) tidak diawali oleh bapak_kode (misal: 53-53CKG)
                if not str(unit).startswith(str(bapak_kode)):
                    # Jika berasal dari UNITAP Excel (contoh 53CKG), rakit dari nol (UID-UP3-ULP)
                    if unitap:
                        uid = str(unitap)[:2] if len(str(unitap)) >= 2 else str(unitap)
                        final_kode_unit = f"{uid}-{unitap}-{unit}"
                    # Jika mewarisi dari akun peng-upload (contoh 53-53CKG), langsung sambung
                    else:
                        final_kode_unit = f"{bapak_kode}-{unit}"

            rec = VerificationRecord(
                session_id=session_id,
                id_pelanggan=id_pel,
                unit=unit, # unit asli (misal 53701) tetap disimpan untuk display di tabel
                kode_nama_biller=kode_nama_biller,
                record_type=record_type,
                stand_ai=stand_ai,
                stand_petugas=stand_bil,
                selisih=selisih,
                merek_ai=merek,
                merek_petugas=nama_bil,
                tipe_ai=tipe,
                lbkb=lbkb,
                status=StatusEnum.VERIFIED_OK if record_type == "match" else StatusEnum.PENDING,
                is_anomaly=(selisih or 0) > ANOMALY_THRESHOLD,
                kode_unit=final_kode_unit
            )
            records.append(rec)
        except Exception:
            continue

    return records


def process_upload(session_id: int, match_bytes: bytes, beda_bytes: bytes, db: Session, kode_unit: str = None):
    """Background task: parse kedua file dan simpan ke DB."""
    try:
        match_records = parse_excel_file(match_bytes, "match", session_id, kode_unit)
        beda_records  = parse_excel_file(beda_bytes,  "beda",  session_id, kode_unit)

        db.bulk_save_objects(match_records + beda_records)

        session = db.query(UploadSession).filter_by(id=session_id).first()
        session.status       = "done"
        session.total_match  = len(match_records)
        session.total_beda   = len(beda_records)
        session.total_records = len(match_records) + len(beda_records)
        db.commit()
    except Exception as e:
        session = db.query(UploadSession).filter_by(id=session_id).first()
        if session:
            session.status = f"error: {str(e)}"
            db.commit()


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    file_match: UploadFile = File(...),
    file_beda: UploadFile = File(...),
    batch_name: str = Form(None),
    bulan_verifikasi: str = Form(None),  # format YYYYMM, misal "202605"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in CAN_UPLOAD:
        raise HTTPException(status_code=403, detail="Hanya UP3 ke atas yang dapat upload file")

    for f in [file_match, file_beda]:
        if not f.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail=f"File '{f.filename}' harus format .xlsx / .xls")

    match_bytes = await file_match.read()
    beda_bytes  = await file_beda.read()

    session = UploadSession(
        uploaded_by=current_user.id,
        batch_name=batch_name,
        bulan_verifikasi=bulan_verifikasi,
        file_match_name=file_match.filename,
        file_beda_name=file_beda.filename,
        status="processing",
        kode_unit=current_user.kode_unit
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    background_tasks.add_task(process_upload, session.id, match_bytes, beda_bytes, db, current_user.kode_unit)
    return {
        "session_id": session.id,
        "status": "processing",
        "message": "File sedang diproses, tunggu beberapa saat"
    }


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from sqlalchemy import or_
    q = db.query(UploadSession)
    
    if current_user.role == RoleEnum.super_admin:
        pass
    elif current_user.role == RoleEnum.verifikator:
        # Hanya tampilkan sesi yang memiliki minimal 1 record dengan assigned_to == current_user.id
        q = q.join(VerificationRecord, VerificationRecord.session_id == UploadSession.id)\
             .filter(VerificationRecord.assigned_to == current_user.id).distinct()
    else:
        if current_user.kode_unit:
            prefixes = [current_user.kode_unit[:i] for i in range(1, len(current_user.kode_unit)+1)]
            q = q.filter(
                or_(
                    UploadSession.kode_unit.is_(None),  # Fallback untuk sesi lama yang belum punya kode_unit
                    UploadSession.kode_unit.like(f"{current_user.kode_unit}%"),
                    UploadSession.kode_unit.in_(prefixes)
                )
            )
            
    q = q.order_by(UploadSession.created_at.desc())
    sessions = q.all()
    result = []
    for s in sessions:
        total_records = s.total_records
        total_match = s.total_match
        total_beda = s.total_beda
        
        # Jika verifikator atau ULP (yang kode_unitnya lebih spesifik dari sesi), hitung ulang
        if current_user.role == RoleEnum.verifikator:
            total_records = db.query(VerificationRecord).filter(
                VerificationRecord.session_id == s.id,
                VerificationRecord.assigned_to == current_user.id,
                VerificationRecord.is_deleted == False
            ).count()
            total_match = db.query(VerificationRecord).filter(
                VerificationRecord.session_id == s.id,
                VerificationRecord.assigned_to == current_user.id,
                VerificationRecord.record_type == 'match',
                VerificationRecord.is_deleted == False
            ).count()
            total_beda = total_records - total_match
        elif current_user.kode_unit and (not s.kode_unit or len(current_user.kode_unit) > len(s.kode_unit)):
            total_records = db.query(VerificationRecord).filter(
                VerificationRecord.session_id == s.id,
                VerificationRecord.kode_unit.like(f"{current_user.kode_unit}%"),
                VerificationRecord.is_deleted == False
            ).count()
            total_match = db.query(VerificationRecord).filter(
                VerificationRecord.session_id == s.id,
                VerificationRecord.kode_unit.like(f"{current_user.kode_unit}%"),
                VerificationRecord.record_type == 'match',
                VerificationRecord.is_deleted == False
            ).count()
            total_beda = total_records - total_match
            
        # Jangan tampilkan sesi jika tidak ada record untuk user ini (kecuali Super Admin atau sesi masih diproses)
        if total_records == 0 and current_user.role != RoleEnum.super_admin and s.status != 'processing':
            continue

        result.append({
            "id": s.id,
            "batch_name": s.batch_name,
            "bulan_verifikasi": s.bulan_verifikasi,
            "file_match_name": s.file_match_name or getattr(s, 'file_ai_name', None),
            "file_beda_name":  s.file_beda_name  or getattr(s, 'file_petugas_name', None),
            "created_at": s.created_at,
            "status": s.status,
            "total_records": total_records,
            "total_match":   total_match,
            "total_beda":    total_beda,
        })
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(UploadSession).filter_by(id=session_id)
    q = apply_scope_filter(q, UploadSession, current_user)
    s = q.first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    return {
        "id": s.id,
        "batch_name": s.batch_name,
        "bulan_verifikasi": s.bulan_verifikasi,
        "file_match_name": s.file_match_name or s.file_ai_name,
        "file_beda_name":  s.file_beda_name  or s.file_petugas_name,
        "created_at": s.created_at,
        "status": s.status,
        "total_records": s.total_records,
        "total_match":   s.total_match,
        "total_beda":    s.total_beda,
    }


def background_delete_session(session_id: int):
    from app.database import SessionLocal
    from app.models import AssignmentBatch, UploadSession
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        # 1. Hapus assignment batches
        db.query(AssignmentBatch).filter_by(session_id=session_id).delete(synchronize_session=False)
        db.commit()

        # 2. Hapus audit_logs yang terkait dengan record di sesi ini secara bertahap (Fix Foreign Key Violation)
        print(f"[{datetime.now()}] [SESSION {session_id}] Menghapus audit_logs...")
        total_audit_deleted = 0
        while True:
            print(f"[{datetime.now()}] [SESSION {session_id}] Menghapus chunk audit_logs... (Total terhapus sejauh ini: {total_audit_deleted})")
            res = db.execute(
                text("""
                    DELETE FROM audit_logs 
                    WHERE id IN (
                        SELECT a.id FROM audit_logs a
                        JOIN verification_records v ON a.record_id = v.id
                        WHERE v.session_id = :sid
                        LIMIT 10000
                    )
                """),
                {"sid": session_id}
            )
            db.commit()
            if res.rowcount == 0:
                break
            total_audit_deleted += res.rowcount
        print(f"[{datetime.now()}] [SESSION {session_id}] audit_logs selesai dihapus. Total: {total_audit_deleted}")

        # 3. Hapus records secara bertahap (chunking via SQL) agar cepat dan tidak kena limit parameter Postgres
        total_deleted = 0
        while True:
            print(f"[{datetime.now()}] [SESSION {session_id}] Menghapus chunk records... (Total terhapus sejauh ini: {total_deleted})")
            res = db.execute(
                text("DELETE FROM verification_records WHERE id IN (SELECT id FROM verification_records WHERE session_id = :sid LIMIT 10000)"),
                {"sid": session_id}
            )
            db.commit()
            if res.rowcount == 0:
                break
            total_deleted += res.rowcount

        # 4. Terakhir hapus sesi, tapi pastikan dulu tidak ada sisa record (mencegah Foreign Key crash jika terjadi race condition)
        count_sisa = db.execute(
            text("SELECT COUNT(*) FROM verification_records WHERE session_id = :sid"),
            {"sid": session_id}
        ).scalar()
        
        if count_sisa == 0:
            db.execute(
                text("DELETE FROM upload_sessions WHERE id = :sid"),
                {"sid": session_id}
            )
            db.commit()
            print(f"[{datetime.now()}] [SESSION {session_id}] Sesi berhasil dihapus total dari database.")
        else:
            print(f"[{datetime.now()}] [SESSION {session_id}] GAGAL HAPUS SESI: Masih ada {count_sisa} data tersisa! Kemungkinan proses lain masih berjalan.")

    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in CAN_UPLOAD:
        raise HTTPException(status_code=403, detail="Hanya role pengunggah yang dapat menghapus sesi")
        
    q = db.query(UploadSession).filter_by(id=session_id)
    q = apply_scope_filter(q, UploadSession, current_user)
    session = q.first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
        
    session.status = "deleting"
    db.commit()
    
    background_tasks.add_task(background_delete_session, session_id)
    return {"message": "Sesi sedang dihapus di latar belakang"}