"""
test_auth.py — Test untuk endpoint /api/auth/*
"""

import pytest


# ─── 1. Login ─────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client, admin_user):
        """Login dengan kredensial valid harus mengembalikan JWT token."""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "Admin@123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        assert data["full_name"] == "Admin Test"

    def test_login_wrong_password(self, client, admin_user):
        """Password salah harus mengembalikan 401."""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "WrongPassword"
        })
        assert resp.status_code == 401

    def test_login_wrong_username(self, client, admin_user):
        """Username tidak ada harus mengembalikan 401."""
        resp = client.post("/api/auth/login", json={
            "username": "username_tidak_ada",
            "password": "Admin@123"
        })
        assert resp.status_code == 401

    def test_login_empty_credentials(self, client):
        """Credential kosong harus mengembalikan 422."""
        resp = client.post("/api/auth/login", json={
            "username": "",
            "password": ""
        })
        # Bisa 401 atau 422 — yang penting BUKAN 200
        assert resp.status_code in (401, 422)

    def test_login_inactive_user(self, client, db, admin_user):
        """User yang dinonaktifkan tidak bisa login."""
        admin_user.is_active = False
        db.add(admin_user)
        db.commit()

        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "Admin@123"
        })
        assert resp.status_code == 401

    def test_token_is_jwt_format(self, client, admin_user):
        """Token harus berformat JWT (tiga bagian dipisah titik)."""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test",
            "password": "Admin@123"
        })
        token = resp.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3, "JWT harus terdiri dari 3 bagian (header.payload.signature)"


# ─── 2. JWT Authentication ────────────────────────────────────────────────────

class TestJWTProtection:
    """Endpoint yang memerlukan auth harus menolak request tanpa/dengan token invalid."""

    PROTECTED_ENDPOINTS = [
        ("PATCH", "/api/records/1"),
        ("POST",  "/api/upload/upload"),
        ("GET",   "/api/notifications/"),
        ("GET",   "/api/notifications/unread-count"),
    ]

    def test_protected_endpoint_no_token(self, client):
        """Request tanpa token harus mendapat 401/403."""
        for method, url in self.PROTECTED_ENDPOINTS:
            resp = getattr(client, method.lower())(url)
            assert resp.status_code in (401, 403), \
                f"{method} {url} seharusnya menolak tanpa token, dapat {resp.status_code}"

    def test_protected_endpoint_invalid_token(self, client):
        """Request dengan token palsu harus mendapat 401."""
        bad_headers = {"Authorization": "Bearer ini.bukan.jwt"}
        for method, url in self.PROTECTED_ENDPOINTS:
            resp = getattr(client, method.lower())(url, headers=bad_headers)
            assert resp.status_code == 401, \
                f"{method} {url} seharusnya menolak token palsu, dapat {resp.status_code}"

    def test_tampered_jwt_rejected(self, client, admin_user, admin_token):
        """Token yang dimodifikasi harus ditolak."""
        # Ambil token asli dan modifikasi signature-nya
        parts = admin_token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.SIGNATURE_PALSU"
        resp = client.get("/api/notifications/", headers={
            "Authorization": f"Bearer {tampered}"
        })
        assert resp.status_code == 401


# ─── 3. Init Admin ────────────────────────────────────────────────────────────

class TestInitAdmin:
    def test_init_admin_creates_user(self, client):
        """init-admin harus bisa membuat user admin."""
        resp = client.post("/api/auth/init-admin")
        assert resp.status_code == 200
        data = resp.json()
        assert "admin" in data.get("message", "").lower() or "username" in data

    def test_init_admin_idempotent(self, client, admin_user):
        """init-admin tidak boleh error jika admin sudah ada."""
        # Buat admin pertama (sudah ada dari fixture)
        # Panggil lagi — harus ok
        resp = client.post("/api/auth/init-admin")
        assert resp.status_code == 200
        assert "sudah ada" in resp.json().get("message", "")
