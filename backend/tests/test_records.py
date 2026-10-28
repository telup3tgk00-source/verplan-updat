"""
test_records.py — Test untuk endpoint /api/records/*
"""

import pytest
from app.models import StatusEnum


class TestGetRecords:
    BASE_URL = "/api/records/"

    def test_get_records_no_auth(self, client, sample_record):
        """
        GET /api/records/ tidak punya auth guard — BUG MEDIUM.
        Test ini mendokumentasikan perilaku saat ini (accessible tanpa token).
        """
        resp = client.get(self.BASE_URL)
        # Saat ini endpoint ini TIDAK protected — mengembalikan 200
        # Seharusnya 401 jika data sensitif
        assert resp.status_code == 200  # Dokumentasi bug: seharusnya 401

    def test_get_records_returns_list(self, client, sample_record):
        """Endpoint mengembalikan list record yang valid."""
        resp = client.get(self.BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_filter_by_session_id(self, client, sample_record, sample_session):
        """Filter session_id harus membatasi hasil."""
        resp = client.get(self.BASE_URL, params={"session_id": sample_session.id})
        assert resp.status_code == 200
        for r in resp.json():
            assert r["session_id"] == sample_session.id

    def test_filter_by_status(self, client, sample_record):
        """Filter status PENDING harus hanya menampilkan record PENDING."""
        resp = client.get(self.BASE_URL, params={"status": "PENDING"})
        assert resp.status_code == 200
        for r in resp.json():
            assert r["status"] == "PENDING"

    def test_filter_by_invalid_status(self, client, sample_record):
        """Filter dengan status tidak valid — tidak boleh crash (harus return 0 atau error terhandani)."""
        resp = client.get(self.BASE_URL, params={"status": "INVALID_STATUS"})
        # Harusnya 200 dengan list kosong atau 422
        assert resp.status_code in (200, 422)

    def test_search_by_idpel(self, client, sample_record):
        """Search dengan idpel sebagian harus menemukan record yang cocok."""
        resp = client.get(self.BASE_URL, params={"search": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert any("123456" in r["id_pelanggan"] for r in data)

    def test_search_nonexistent_idpel(self, client, sample_record):
        """Search idpel yang tidak ada harus mengembalikan list kosong."""
        resp = client.get(self.BASE_URL, params={"search": "000000000000"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pagination_skip_limit(self, client, db, sample_session):
        """Pagination skip/limit harus berfungsi dengan benar."""
        from app.models import VerificationRecord
        # Buat 5 record
        for i in range(5):
            db.add(VerificationRecord(
                session_id=sample_session.id,
                id_pelanggan=f"10000000{i:04d}",
                record_type="beda",
                status=StatusEnum.PENDING,
                is_deleted=False
            ))
        db.commit()

        resp_all = client.get(self.BASE_URL, params={"limit": 100})
        resp_limited = client.get(self.BASE_URL, params={"limit": 2, "skip": 0})
        resp_skipped = client.get(self.BASE_URL, params={"limit": 2, "skip": 2})

        total = len(resp_all.json())
        assert len(resp_limited.json()) <= 2
        assert len(resp_skipped.json()) <= 2
        # Tidak boleh ada overlap antara page 1 dan page 2
        ids_page1 = {r["id"] for r in resp_limited.json()}
        ids_page2 = {r["id"] for r in resp_skipped.json()}
        assert ids_page1.isdisjoint(ids_page2)

    def test_anomaly_only_filter(self, client, db, sample_session):
        """Filter anomaly_only harus hanya menampilkan record dengan is_anomaly=True."""
        from app.models import VerificationRecord
        db.add(VerificationRecord(
            session_id=sample_session.id,
            id_pelanggan="ANOMALY001",
            record_type="beda",
            stand_ai=10000,
            stand_petugas=100,
            selisih=9900,
            is_anomaly=True,
            is_deleted=False
        ))
        db.commit()

        resp = client.get(self.BASE_URL, params={"anomaly_only": True})
        assert resp.status_code == 200
        for r in resp.json():
            assert r["is_anomaly"] is True


class TestUpdateRecord:
    def test_update_record_requires_auth(self, client, sample_record):
        """PATCH tanpa token harus ditolak."""
        resp = client.patch(f"/api/records/{sample_record.id}", json={
            "status": "VERIFIED_OK",
            "catatan": "Test",
        })
        assert resp.status_code in (401, 403)

    def test_update_record_to_verified_ok(self, client, verif_headers, sample_record):
        """Update record ke VERIFIED_OK harus berhasil."""
        resp = client.patch(
            f"/api/records/{sample_record.id}",
            json={"status": "VERIFIED_OK", "catatan": "Sudah dicek"},
            headers=verif_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "VERIFIED_OK"
        assert data["catatan"] == "Sudah dicek"

    def test_update_record_to_reject_with_reason(self, client, verif_headers, sample_record):
        """Update ke VERIFIED_REJECT dengan reason_type."""
        resp = client.patch(
            f"/api/records/{sample_record.id}",
            json={
                "status": "VERIFIED_REJECT",
                "catatan": "Foto tidak sesuai",
                "reason_type": "FOTO_BEDA",
            },
            headers=verif_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "VERIFIED_REJECT"

    def test_update_nonexistent_record(self, client, verif_headers):
        """PATCH record yang tidak ada harus 404."""
        resp = client.patch(
            "/api/records/99999",
            json={"status": "VERIFIED_OK", "catatan": ""},
            headers=verif_headers
        )
        assert resp.status_code == 404

    def test_update_deleted_record(self, client, verif_headers, db, sample_session):
        """PATCH record yang sudah dihapus (is_deleted=True) harus 404."""
        from app.models import VerificationRecord
        rec = VerificationRecord(
            session_id=sample_session.id,
            id_pelanggan="DELETED001",
            record_type="beda",
            is_deleted=True,
            status=StatusEnum.PENDING
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        resp = client.patch(
            f"/api/records/{rec.id}",
            json={"status": "VERIFIED_OK", "catatan": ""},
            headers=verif_headers
        )
        assert resp.status_code == 404

    def test_update_creates_audit_log(self, client, verif_headers, sample_record, db):
        """Update record harus membuat audit log entry."""
        from app.models import AuditLog
        before_count = db.query(AuditLog).count()

        client.patch(
            f"/api/records/{sample_record.id}",
            json={"status": "VERIFIED_OK", "catatan": "Audit test"},
            headers=verif_headers
        )
        db.expire_all()  # Refresh session

        after_count = db.query(AuditLog).count()
        assert after_count > before_count

    def test_update_reject_sends_notification(self, client, verif_headers, sample_record, admin_user, db):
        """Update ke VERIFIED_REJECT harus membuat notifikasi untuk admin."""
        from app.models import Notification
        before_count = db.query(Notification).filter_by(user_id=admin_user.id).count()

        client.patch(
            f"/api/records/{sample_record.id}",
            json={"status": "VERIFIED_REJECT", "catatan": "Penolakan test"},
            headers=verif_headers
        )
        db.expire_all()

        after_count = db.query(Notification).filter_by(user_id=admin_user.id).count()
        assert after_count > before_count, "Notifikasi harus dikirim ke admin saat penolakan"

    def test_update_invalid_status_value(self, client, verif_headers, sample_record):
        """Update dengan status tidak valid harus ditolak dengan 422."""
        resp = client.patch(
            f"/api/records/{sample_record.id}",
            json={"status": "INVALID_STATUS", "catatan": ""},
            headers=verif_headers
        )
        assert resp.status_code == 422


class TestRecordSummary:
    def test_stats_summary_endpoint(self, client, sample_record):
        """GET /api/records/stats/summary harus mengembalikan statistik."""
        resp = client.get("/api/records/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "pending" in data
        assert "verified_ok" in data
        assert "verified_reject" in data
        assert "progress_pct" in data

    def test_stats_filter_by_session(self, client, sample_record, sample_session):
        """Stats dengan filter session_id harus menghitung hanya record di sesi itu."""
        resp = client.get("/api/records/stats/summary", params={"session_id": sample_session.id})
        assert resp.status_code == 200
        data = resp.json()
        # Sample record adalah PENDING
        assert data["pending"] >= 1

    def test_stats_progress_pct_zero_when_empty(self, client):
        """Progress pct harus 0 ketika tidak ada data."""
        resp = client.get("/api/records/stats/summary", params={"session_id": 99999})
        assert resp.status_code == 200
        assert resp.json()["progress_pct"] == 0
        assert resp.json()["total"] == 0
