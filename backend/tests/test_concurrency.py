"""
test_concurrency.py — Race conditions & concurrency tests
"""
import concurrent.futures
import pytest
from app.models import StatusEnum

class TestConcurrency:

    def test_concurrent_patch_same_record(self, client, verif_headers, admin_headers, sample_record, db):
        """Simulasi 2 user mengupdate record yang sama persis di waktu yang hampir bersamaan."""
        
        def patch_record(headers, status, catatan):
            # TestClient tidak default async, jadi kita gunakan threading
            return client.patch(
                f"/api/records/{sample_record.id}",
                json={"status": status, "catatan": catatan},
                headers=headers
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(patch_record, verif_headers, "VERIFIED_OK", "Updated by verif")
            future2 = executor.submit(patch_record, admin_headers, "VERIFIED_REJECT", "Updated by admin")
            
            resp1 = future1.result()
            resp2 = future2.result()

        # Keduanya mungkin berhasil secara HTTP (200), tapi hasil akhir di DB hanya ada satu state.
        # SQLite secara default menghandle concurrency dengan locking (write lock).
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        
        # Cek audit log, harus ada 2 entry berurutan.
        db.expire_all()
        from app.models import AuditLog
        logs = db.query(AuditLog).filter_by(record_id=sample_record.id).order_by(AuditLog.id.asc()).all()
        assert len(logs) >= 2

    def test_concurrent_uploads(self, client, admin_headers, valid_match_excel, valid_beda_excel):
        """Simulasi 2 upload batch secara bersamaan."""
        import io
        def upload_batch(name):
            files = {
                "file_match": ("match.xlsx", io.BytesIO(valid_match_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "file_beda":  ("beda.xlsx", io.BytesIO(valid_beda_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            }
            return client.post("/api/upload/upload", files=files, data={"batch_name": name}, headers=admin_headers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_batch, f"Batch-Concurrent-{i}") for i in range(3)]
            results = [f.result() for f in futures]
            
        for r in results:
            assert r.status_code == 200
