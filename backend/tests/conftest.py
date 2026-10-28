"""
conftest.py — Pytest fixtures untuk PLN Verifikasi Test Suite
Menggunakan database SQLite in-memory agar tes tidak memodifikasi DB produksi.
"""

import io
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set TEST environment SEBELUM import app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///./test_pln.db"

from app.database import Base, get_db
from app.main import app
from app.models import User, RoleEnum, VerificationRecord, UploadSession, StatusEnum
from app.routers.auth import pwd_context

# ─── Test DB Setup ────────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_pln.db"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override dependency sebelum client dibuat
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Buat schema DB untuk seluruh sesi test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Hapus file DB test
    if os.path.exists("test_pln.db"):
        try:
            os.remove("test_pln.db")
        except PermissionError:
            pass


@pytest.fixture(autouse=True)
def clean_tables():
    """Reset data tabel sebelum setiap test (kecuali schema)."""
    db = TestingSessionLocal()
    tables = [
        "audit_logs", "notifications", "assignment_batches",
        "verification_records", "upload_sessions", "users", "reason_options"
    ]
    for table in tables:
        db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
    db.commit()
    db.close()


@pytest.fixture
def client():
    """TestClient tanpa autentikasi."""
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def db():
    """DB session untuk setup data langsung."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─── User Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    user = User(
        username="admin_test",
        password_hash=pwd_context.hash("Admin@123"),
        full_name="Admin Test",
        role=RoleEnum.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def verifikator_user(db):
    user = User(
        username="verif_test",
        password_hash=pwd_context.hash("Verif@123"),
        full_name="Verifikator Test",
        role=RoleEnum.verifikator,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user):
    """Login sebagai admin dan dapatkan token JWT."""
    resp = client.post("/api/auth/login", json={
        "username": "admin_test",
        "password": "Admin@123"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def verif_token(client, verifikator_user):
    """Login sebagai verifikator dan dapatkan token JWT."""
    resp = client.post("/api/auth/login", json={
        "username": "verif_test",
        "password": "Verif@123"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def verif_headers(verif_token):
    return {"Authorization": f"Bearer {verif_token}"}


# ─── Data Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_session(db, admin_user):
    session = UploadSession(
        uploaded_by=admin_user.id,
        batch_name="Batch Test",
        bulan_verifikasi="202605",
        file_match_name="match.xlsx",
        file_beda_name="beda.xlsx",
        status="done",
        total_records=2,
        total_match=1,
        total_beda=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def sample_record(db, sample_session):
    record = VerificationRecord(
        session_id=sample_session.id,
        id_pelanggan="123456789012",
        record_type="beda",
        stand_ai=1500.0,
        stand_petugas=1000.0,
        selisih=500.0,
        merek_ai="ITRON",
        merek_petugas="ITRON",
        status=StatusEnum.PENDING,
        is_anomaly=False,
        is_deleted=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ─── Excel File Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def valid_match_excel():
    """Buat file Excel match yang valid sebagai bytes."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih", "Merek", "Tipe Stan"])
    ws.append(["123456789001", 1500, 1500, 0, "ITRON", "1P"])
    ws.append(["123456789002", 2000, 2000, 0, "SANXING", "1P"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def valid_beda_excel():
    """Buat file Excel beda yang valid sebagai bytes."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih", "Merek", "Tipe Stan"])
    ws.append(["999888777001", 1500, 1000, 500, "ITRON", "1P"])
    ws.append(["999888777002", 3000, 100, 2900, "LANNIS", "3P"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def invalid_excel_no_idpel():
    """Excel tanpa kolom ID Pelanggan."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Stand AI", "Stand Biller"])
    ws.append([1500, 1500])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def empty_excel():
    """Excel yang benar-benar kosong (header saja)."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID Pelanggan", "Stand AI", "Stand Biller"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
