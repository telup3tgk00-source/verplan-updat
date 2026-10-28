from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import VerificationRecord, StatusEnum, User
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.cell import WriteOnlyCell
from datetime import datetime
import io
import threading

router = APIRouter()

from sqlalchemy import or_, and_
from app.routers.auth import get_current_user
from app.permissions import CAN_EXPORT, apply_scope_filter

def _build_query(db: Session, session_id: int, filter_status: str, record_type: str, operator_id, current_user, bulan: str = None):
    """Build the filtered SQLAlchemy query (returns query object, not results)."""
    q = db.query(VerificationRecord).filter_by(is_deleted=False)
    
    if session_id:
        q = q.filter(VerificationRecord.session_id == session_id)
        
    if bulan:
        from app.models import UploadSession
        q = q.join(UploadSession, VerificationRecord.session_id == UploadSession.id)\
             .filter(UploadSession.bulan_verifikasi == bulan)
             
    q = apply_scope_filter(q, VerificationRecord, current_user)

    if filter_status != "all":
        q = q.filter(VerificationRecord.status == filter_status)

    if record_type == "match":
        q = q.filter(
            or_(
                VerificationRecord.record_type == "match",
                and_(
                    VerificationRecord.record_type == "beda",
                    VerificationRecord.status == StatusEnum.VERIFIED_OK,
                    VerificationRecord.corrected_stand == VerificationRecord.stand_petugas
                )
            )
        )
    elif record_type == "beda":
        q = q.filter(
            and_(
                VerificationRecord.record_type == "beda",
                or_(
                    VerificationRecord.status != StatusEnum.VERIFIED_OK,
                    VerificationRecord.corrected_stand == None,
                    VerificationRecord.corrected_stand != VerificationRecord.stand_petugas
                )
            )
        )

    if operator_id:
        q = q.filter(VerificationRecord.assigned_to == operator_id)

    # Hanya ambil kolom yang dibutuhkan (jauh lebih hemat RAM dari full ORM objects)
    q = q.with_entities(
        VerificationRecord.unit,
        VerificationRecord.id_pelanggan,
        VerificationRecord.kode_nama_biller,
        VerificationRecord.record_type,
        VerificationRecord.stand_ai,
        VerificationRecord.stand_petugas,
        VerificationRecord.selisih,
        VerificationRecord.merek_ai,
        VerificationRecord.merek_petugas,
        VerificationRecord.tipe_ai,
        VerificationRecord.tipe_petugas,
        VerificationRecord.status,
        VerificationRecord.reason_type,
        VerificationRecord.corrected_stand,
        VerificationRecord.catatan,
        VerificationRecord.lbkb,
        VerificationRecord.assigned_to,
        VerificationRecord.verified_at
    )
    return q


def _generate_xlsx_bytes(
    db: Session,
    session_id: int,
    filter_status: str,
    record_type: str,
    operator_id,
    current_user,
    bulan: str = None
) -> io.BytesIO:
    """
    Build the Excel file in memory using write_only mode and yield_per
    to keep RAM usage low even for 300k+ records.
    Returns a BytesIO buffer ready for streaming.
    """
    from app.models import User, ReasonOption, RoleEnum

    users = {u.id: u.full_name for u in db.query(User).all()}
    
    reasons_query = db.query(ReasonOption)
    if current_user.role != RoleEnum.super_admin:
        uid_code = current_user.kode_unit[:2] if current_user.kode_unit else '17'
        reasons_query = reasons_query.filter(ReasonOption.uid_code == uid_code)
            
    reasons_map = {r.value: r.label for r in reasons_query.all()}

    q = _build_query(db, session_id, filter_status, record_type, operator_id, current_user, bulan)

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Data Verifikasi")

    headers = [
        "Unit", "ID Pelanggan", "Kode Biller", "Record Type",
        "Stand", "Stand Biller", "Selisih",
        "Merek AI", "Merek Biller", "Tipe AI", "Tipe Biller",
        "Status Verifikasi", "Alasan", "Koreksi Stand", "Catatan",
        "LBKB", "Verifikator", "Waktu Verifikasi"
    ]

    header_row = []
    for h in headers:
        cell = WriteOnlyCell(ws, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0D2A5E")
        header_row.append(cell)
    ws.append(header_row)

    # yield_per: ambil 500 baris per batch dari DB → RAM konstan, tidak spike
    for rec in q.yield_per(500):
        if rec.status:
            status_val = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
        else:
            status_val = "PENDING"

        reason_str = reasons_map.get(rec.reason_type, rec.reason_type) if rec.reason_type else ""

        display_stand_ai = rec.corrected_stand if rec.corrected_stand is not None else rec.stand_ai

        if display_stand_ai is not None and rec.stand_petugas is not None:
            display_selisih = float(display_stand_ai) - float(rec.stand_petugas)
        else:
            display_selisih = rec.selisih

        display_record_type = (rec.record_type or "").upper()

        rec_status_str = rec.status.value if hasattr(rec.status, "value") else str(rec.status) if rec.status else ""
        if rec.record_type == "beda" and rec_status_str == "VERIFIED_OK" and rec.corrected_stand == rec.stand_petugas:
            display_record_type = "MATCH (KOREKSI)"

        ws.append([
            rec.unit or "", rec.id_pelanggan, rec.kode_nama_biller or "",
            display_record_type, display_stand_ai, rec.stand_petugas, display_selisih,
            rec.merek_ai, rec.merek_petugas, rec.tipe_ai, rec.tipe_petugas,
            status_val, reason_str, rec.corrected_stand or "", rec.catatan or "",
            rec.lbkb or "", users.get(rec.assigned_to, "-") if rec.assigned_to else "-",
            rec.verified_at.strftime("%Y-%m-%d %H:%M") if rec.verified_at else ""
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _stream_xlsx_in_background(db: Session, session_id: int, filter_status: str, record_type: str, operator_id, current_user, bulan: str = None):
    """
    Generator yang membangun XLSX di background thread, kemudian
    yield hasilnya dalam chunk 1MB agar Nginx tidak timeout.

    Cara kerja:
    1. Thread terpisah membangun XLSX (blokir I/O berat, jangan di event loop)
    2. Setelah selesai, generator yield chunk-chunk data ke Nginx
    3. Nginx menerima data dalam chunk → proxy_read_timeout tidak ter-trigger
    """
    result_holder = {}
    error_holder = {}

    def worker():
        try:
            result_holder["buf"] = _generate_xlsx_bytes(
                db, session_id, filter_status, record_type, operator_id, current_user, bulan
            )
        except Exception as e:
            error_holder["err"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join()  # Tunggu selesai (synchronous — handler ini dipanggil di thread pool FastAPI)

    if "err" in error_holder:
        raise error_holder["err"]

    buf = result_holder["buf"]
    chunk_size = 1024 * 1024  # 1 MB per chunk
    while True:
        chunk = buf.read(chunk_size)
        if not chunk:
            break
        yield chunk


@router.get("/")
def export_excel(
    session_id: int = Query(None),
    bulan: str = Query(None),
    filter_status: str = Query("all"),
    record_type: str = Query("all"),
    operator_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from fastapi import HTTPException
    import app.models
    if current_user.role not in CAN_EXPORT:
        raise HTTPException(status_code=403, detail="Hanya role ULP ke atas yang dapat mengekspor data")

    if not session_id and not bulan:
        raise HTTPException(status_code=400, detail="Harus menyertakan session_id atau bulan")

    fname = f"verifikasi_kwh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        _stream_xlsx_in_background(db, session_id, filter_status, record_type, operator_id, current_user, bulan),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )