"""
test_edge_cases.py — Edge cases, human error, and idempotency tests
"""
import io
import pytest

class TestHumanErrorValidation:
    # 1. Upload file non-Excel
    def test_upload_pdf_file(self, client, admin_headers):
        files = {
            "file_match": ("document.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf"),
            "file_beda":  ("image.png", io.BytesIO(b"\x89PNG..."), "image/png"),
        }
        resp = client.post("/api/upload/upload", files=files, data={"batch_name": "Test PDF"}, headers=admin_headers)
        assert resp.status_code == 400
        assert "format" in resp.json()["detail"].lower() or ".xlsx" in resp.json()["detail"].lower()

    # 2. JSESSIONID invalid format
    def test_invalid_jsessionid_format(self, client, admin_headers):
        invalid_cookies = [
            "JSESSIONID=; TS01=123", # kosong valuenya
            "JSESSIONID", # tanpa =
            "JSESSIONID=123", # mungkin terlalu pendek, tapi sistem saat ini ngecek eksistensi string JSESSIONID.
            # sistem hanya cek 'JSESSIONID' in string, jadi let's test if it handles completely random string.
            "RANDOM_COOKIE=ABCDEFG1234567890"
        ]
        for cookie in invalid_cookies:
            resp = client.post("/api/foto/session", json={
                "cookie_string": cookie,
                "set_by": "tester"
            }, headers=admin_headers)
            # Kalau tidak mengandung JSESSIONID, harus 400
            if "JSESSIONID" not in cookie:
                assert resp.status_code == 400
                assert "JSESSIONID" in resp.json()["detail"]

    # 3. IDPEL format salah
    def test_idpel_with_spaces_and_letters(self, client, admin_headers, valid_beda_excel):
        """Excel dengan spasi dan huruf di ID Pelanggan harus dihandle (misal di-strip atau diabaikan jika nan)."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih"])
        # String kotor, string huruf, empty spaces
        ws.append(["  123456789012  ", 100, 100, 0]) 
        ws.append(["IDPEL-HURUF", 100, 100, 0])
        ws.append(["", 100, 100, 0]) 

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        dirty_match = buf.read()

        files = {
            "file_match": ("match.xlsx", io.BytesIO(dirty_match), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_beda":  ("beda.xlsx", io.BytesIO(valid_beda_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp = client.post("/api/upload/upload", files=files, data={"batch_name": "Dirty Data"}, headers=admin_headers)
        assert resp.status_code == 200
        # Background task processing
        # Idealnya ID yang kosong di-skip, yang ada spasi di-strip

    # 4. Double Submit (Idempotency check / duplicate batch check)
    def test_double_submit_same_file(self, client, admin_headers, valid_match_excel, valid_beda_excel):
        files1 = {
            "file_match": ("match.xlsx", io.BytesIO(valid_match_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_beda":  ("beda.xlsx", io.BytesIO(valid_beda_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        files2 = {
            "file_match": ("match.xlsx", io.BytesIO(valid_match_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "file_beda":  ("beda.xlsx", io.BytesIO(valid_beda_excel), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        resp1 = client.post("/api/upload/upload", files=files1, data={"batch_name": "Idempotent"}, headers=admin_headers)
        resp2 = client.post("/api/upload/upload", files=files2, data={"batch_name": "Idempotent"}, headers=admin_headers)
        
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Saat ini sistem mengizinkan upload berkali-kali. Ini mendokumentasikan bahwa tidak ada idempotent guard.
        # Bisa jadi future improvement.
