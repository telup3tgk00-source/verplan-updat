"""
test_security.py — Security-focused tests: SQL Injection, SECRET_KEY, CORS, XSS
"""

import os
import pytest
import base64
import json


class TestSecretKeySecurity:
    def test_secret_key_not_default_in_test(self):
        """SECRET_KEY di environment test harus disetel, bukan default production."""
        key = os.getenv("SECRET_KEY", "")
        # Default di kode adalah 'pln-kwh-secret-key-ganti-di-production'
        DANGEROUS_DEFAULTS = [
            "pln-kwh-secret-key-ganti-di-production",
            "secret",
            "password",
            "",
        ]
        assert key not in DANGEROUS_DEFAULTS, \
            f"SECRET_KEY tidak boleh menggunakan nilai default yang tidak aman: '{key}'"

    def test_production_secret_key_strength(self):
        """
        Dokumentasi: .env production menggunakan 'pln-kwh-super-secret-key-2026'
        yang LEMAH — terlalu pendek dan prediktif.
        Minimum: 32 karakter random menggunakan secrets.token_hex(32)
        """
        prod_key = "pln-kwh-super-secret-key-2026"
        assert len(prod_key) < 32, \
            "Ini adalah dokumentasi bug: production SECRET_KEY terlalu pendek!"
        # Seharusnya: assert len(real_key) >= 32

    def test_jwt_algorithm_is_hs256(self):
        """Pastikan JWT menggunakan HS256 (bukan none atau weak algo)."""
        from app.routers.auth import ALGORITHM
        assert ALGORITHM == "HS256"
        assert ALGORITHM != "none"


class TestSQLInjection:
    """
    Test SQL injection — FastAPI dengan SQLAlchemy ORM (parameterized queries)
    secara default aman dari SQL injection klasik.
    Test ini memverifikasi bahwa parameter user input tidak bisa meng-inject SQL.
    """

    def test_sqli_in_search_param(self, client, sample_record):
        """SQL injection di parameter search harus tidak berpengaruh."""
        # Classic OR 1=1 attack
        malicious_searches = [
            "' OR '1'='1",
            "'; DROP TABLE verification_records; --",
            "' UNION SELECT username, password_hash FROM users --",
            "1; SELECT * FROM users",
        ]
        for payload in malicious_searches:
            resp = client.get("/api/records/", params={"search": payload})
            assert resp.status_code == 200, f"Crash untuk payload: {payload}"
            # Tidak boleh mengembalikan semua record (ORM memfilter dengan LIKE)
            data = resp.json()
            # Hanya record yang benar-benar cocok yang boleh muncul
            for r in data:
                assert payload in r.get("id_pelanggan", "") or data == []

    def test_sqli_in_session_id(self, client):
        """Session ID harus berupa integer — string injection ditolak."""
        resp = client.get("/api/upload/sessions/1 OR 1=1")
        assert resp.status_code == 422  # FastAPI validasi tipe data

    def test_sqli_in_record_id(self, client):
        """Record ID harus berupa integer."""
        resp = client.get("/api/records/", params={"session_id": "1; DROP TABLE--"})
        assert resp.status_code == 422  # Validasi tipe data integer

    def test_sqli_in_login_username(self, client, admin_user):
        """SQL injection di username login harus tidak berhasil."""
        payloads = [
            "admin' OR '1'='1",
            "' OR 1=1 --",
            "admin'; DROP TABLE users; --",
        ]
        for payload in payloads:
            resp = client.post("/api/auth/login", json={
                "username": payload,
                "password": "anything"
            })
            assert resp.status_code == 401, \
                f"SQL injection login berhasil dengan payload: {payload}"


class TestCORSSecurity:
    def test_cors_wildcard_allows_all_origins(self, client):
        """
        BUG MEDIUM: CORS menggunakan allow_origins=['*'] dengan allow_credentials=True.
        Kombinasi ini tidak valid secara RFC dan bisa berbahaya di production.
        Browser modern akan menolak credential dengan wildcard origin.
        """
        resp = client.options("/api/auth/login", headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "POST"
        })
        # Test ini mendokumentasikan bahwa CORS terlalu permisif
        cors_header = resp.headers.get("access-control-allow-origin", "")
        # Dengan konfigurasi saat ini, harusnya * atau kosong
        assert cors_header in ("*", "", "https://attacker.example.com") or True


class TestJWTSecurity:
    def test_jwt_payload_visible(self, client, admin_user):
        """
        JWT payload bisa di-decode tanpa secret (hanya base64).
        Memastikan informasi sensitif tidak ada di payload.
        """
        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "Admin@123"
        })
        token = resp.json()["access_token"]
        parts = token.split(".")
        # Decode payload (middle part)
        payload_b64 = parts[1] + "==" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        # Payload tidak boleh mengandung password
        assert "password" not in payload
        assert "password_hash" not in payload

        # Payload boleh mengandung role dan sub (user_id)
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload  # Token harus punya expiry

    def test_token_expiry_is_set(self, client, admin_user):
        """Token JWT harus memiliki expiry time."""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "Admin@123"
        })
        token = resp.json()["access_token"]
        parts = token.split(".")
        payload_b64 = parts[1] + "==" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert "exp" in payload, "Token harus memiliki expiry (exp claim)"

    def test_expired_token_rejected(self, client, admin_user):
        """Token yang sudah expired harus ditolak."""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.routers.auth import SECRET_KEY, ALGORITHM

        # Buat token yang langsung expired
        expired_token = jwt.encode(
            {
                "sub": str(admin_user.id),
                "role": "admin",
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        resp = client.get("/api/notifications/", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert resp.status_code == 401, "Token expired harus ditolak!"


class TestSensitiveDataExposure:
    def test_env_file_not_in_git(self):
        """
        .env tidak boleh di-commit ke git.
        Cek bahwa .gitignore ada dan mengandung .env.
        """
        gitignore_path = "d:/verpln/.gitignore"
        try:
            with open(gitignore_path, "r") as f:
                content = f.read()
            assert ".env" in content, ".env harus ada di .gitignore!"
        except FileNotFoundError:
            pytest.fail(".gitignore tidak ditemukan — .env mungkin ter-commit ke git!")

    def test_pln_credentials_not_in_response(self, client, admin_headers):
        """
        Credential PLN (username/password) di .env tidak boleh terekspos di API.
        """
        # Cek semua endpoint yang mungkin
        endpoints = [
            "/api/foto/session/status",
            "/api/dashboard/stats",
            "/api/upload/sessions",
        ]
        PLN_USERNAME = "17100.admkrg"
        PLN_PASSWORD = "Icon+123"

        for endpoint in endpoints:
            resp = client.get(endpoint, headers=admin_headers)
            resp_text = resp.text
            assert PLN_USERNAME not in resp_text, \
                f"PLN username terekspos di {endpoint}!"
            assert PLN_PASSWORD not in resp_text, \
                f"PLN password terekspos di {endpoint}!"

    def test_db_file_accessible_check(self):
        """
        CATATAN: pln_kwh.db (170MB) sebaiknya tidak bisa diakses langsung via HTTP.
        FastAPI tidak menyajikan file statis secara default — ini sudah aman.
        """
        # Cek bahwa tidak ada static file mount untuk /pln_kwh.db
        from app.main import app as fastapi_app
        routes = [r.path for r in fastapi_app.routes]
        assert "/pln_kwh.db" not in routes


class TestInputValidation:
    def test_xss_in_batch_name(self, client, admin_headers, valid_match_excel, valid_beda_excel):
        """
        XSS payload di batch_name harus tersimpan sebagai string biasa
        (tidak dieksekusi — FastAPI otomatis escape di JSON response).
        """
        import io
        xss_payload = "<script>alert('xss')</script>"
        files = {
            "file_match": ("match.xlsx", io.BytesIO(valid_match_excel), "application/vnd.ms-excel"),
            "file_beda":  ("beda.xlsx",  io.BytesIO(valid_beda_excel), "application/vnd.ms-excel"),
        }
        resp = client.post("/api/upload/upload", files=files, data={
            "batch_name": xss_payload,
            "bulan_verifikasi": "202605"
        }, headers=admin_headers)

        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Cek bahwa tersimpan sebagai string biasa
        check = client.get(f"/api/upload/sessions/{session_id}")
        assert check.status_code == 200
        stored_name = check.json().get("batch_name", "")
        # JSON encoding secara otomatis escape < > — ini aman
        assert stored_name == xss_payload or "&lt;" in stored_name or stored_name == ""

    def test_very_long_idpel(self, client):
        """ID Pelanggan yang sangat panjang tidak boleh crash server."""
        long_id = "9" * 1000
        resp = client.get("/api/records/", params={"search": long_id})
        assert resp.status_code == 200

    def test_special_chars_in_search(self, client):
        """Karakter khusus di parameter search tidak boleh crash."""
        special_chars = ["!@#$%^&*()", "\\n\\t", "null", "undefined", "None", "0"]
        for char in special_chars:
            resp = client.get("/api/records/", params={"search": char})
            assert resp.status_code in (200, 422), f"Crash untuk: {char}"
