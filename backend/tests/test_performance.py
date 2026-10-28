"""
test_performance.py — Performance & Load test
"""
import io
import pytest
import openpyxl

class TestPerformance:
    def test_upload_excel_1000_plus_rows(self, client, admin_headers):
        """Test upload Excel dengan lebih dari 1000 baris."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih", "Merek", "Tipe Stan"])
        
        for i in range(1500):
            ws.append([f"10000{i:04d}", 2000, 1000, 1000, "ITRON", "1P"])
            
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        large_bytes = buf.read()

        files = {
            "file_match": ("match.xlsx", io.BytesIO(large_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_beda":  ("beda.xlsx", io.BytesIO(large_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        
        resp = client.post("/api/upload/upload", files=files, data={"batch_name": "Perf 1500"}, headers=admin_headers)
        assert resp.status_code == 200
        # Background task processing
        session_id = resp.json()["session_id"]
        assert session_id > 0

    def test_upload_excel_greater_than_10mb(self, client, admin_headers):
        """Simulasi file berukuran sangat besar (>10MB). Karena openpyxl lambat generate file raksasa,
        kita akan mensimulasikan padding di file valid."""
        
        # Buat file excel valid kecil
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih"])
        ws.append(["123456789", 100, 100, 0])
        buf = io.BytesIO()
        wb.save(buf)
        excel_bytes = buf.getvalue()
        
        # Padding file agar ukurannya lebih dari 10MB (FastAPI UploadFile menggunakan SpooledTemporaryFile di disk jika > 1MB)
        # Menambah bytes garbage di akhir file bisa merusak Excel format, tapi fastapi body parser akan menerimanya.
        large_content = excel_bytes + (b"0" * 10_000_000) # 10MB padding
        
        files = {
            "file_match": ("match.xlsx", io.BytesIO(large_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_beda":  ("beda.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        
        resp = client.post("/api/upload/upload", files=files, data={"batch_name": "Perf 10MB+"}, headers=admin_headers)
        
        # Server harusnya menerima request (200), masalah korup file di-handle oleh background task.
        assert resp.status_code == 200
