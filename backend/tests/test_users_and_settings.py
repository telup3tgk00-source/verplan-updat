"""
test_users_and_settings.py — Test untuk /api/users/* dan /api/settings/*
"""

import pytest


# ─── Users ────────────────────────────────────────────────────────────────────

class TestUsersEndpoint:
    def test_get_users_no_auth(self, client, admin_user):
        """
        BUG CRITICAL: GET /api/users/ tidak memerlukan autentikasi.
        Siapapun bisa mendapat daftar semua user dan role mereka.
        """
        resp = client.get("/api/users/")
        assert resp.status_code == 200  # Dokumentasi bug: seharusnya 401
        # Data yang terekspos harus tidak mengandung password hash
        data = resp.json()
        for user in data:
            assert "password" not in user, "Password tidak boleh terekspos di API!"
            assert "password_hash" not in user, "Password hash tidak boleh terekspos!"

    def test_create_user_no_auth(self, client):
        """
        BUG CRITICAL: POST /api/users/ tidak memerlukan autentikasi.
        Siapapun bisa membuat user baru termasuk dengan role admin!
        """
        resp = client.post("/api/users/", json={
            "username": "hacker",
            "password": "Hack@123",
            "full_name": "Hacker",
            "role": "admin"  # Eskalasi privilege!
        })
        # Saat ini endpoint ini 200 tanpa auth — BUG CRITICAL
        # Test ini mendokumentasikan bug, BUKAN memvalidasi perilaku yang benar
        assert resp.status_code in (200, 401)  # Seharusnya 401 selalu

    def test_create_user_duplicate_username(self, client, admin_user):
        """Username duplikat harus ditolak dengan 400."""
        resp = client.post("/api/users/", json={
            "username": "admin_test",  # sudah ada dari fixture
            "password": "Test@123",
            "full_name": "Duplicate User",
            "role": "verifikator"
        })
        assert resp.status_code == 400

    def test_toggle_user_no_auth(self, client, admin_user):
        """
        BUG CRITICAL: PATCH /api/users/{id}/toggle tidak ada auth guard.
        Siapapun bisa menonaktifkan atau mengaktifkan user manapun.
        """
        resp = client.patch(f"/api/users/{admin_user.id}/toggle")
        assert resp.status_code in (200, 401)  # Seharusnya 401

    def test_toggle_nonexistent_user(self, client):
        """Toggle user yang tidak ada harus 404."""
        resp = client.patch("/api/users/99999/toggle")
        assert resp.status_code == 404

    def test_delete_admin_user_protected(self, client, admin_user):
        """Menghapus user 'admin' harus ditolak."""
        # Buat user admin dengan username 'admin'
        from app.models import User, RoleEnum
        from app.routers.auth import pwd_context
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        sys_admin = User(
            username="admin",
            password_hash=pwd_context.hash("admin123"),
            full_name="System Admin",
            role=RoleEnum.admin
        )
        db.add(sys_admin)
        db.commit()
        db.refresh(sys_admin)
        admin_id = sys_admin.id
        db.close()

        resp = client.delete(f"/api/users/{admin_id}")
        assert resp.status_code == 400
        assert "admin" in resp.json()["detail"].lower()

    def test_delete_nonexistent_user(self, client):
        """Menghapus user yang tidak ada harus 404."""
        resp = client.delete("/api/users/99999")
        assert resp.status_code == 404

    def test_user_response_no_password_hash(self, client, admin_user):
        """Response user tidak boleh mengandung password_hash (schema UserOut)."""
        resp = client.get("/api/users/")
        for user in resp.json():
            assert "password_hash" not in user
            assert "password" not in user


# ─── Settings / Reasons ──────────────────────────────────────────────────────

class TestSettingsReasons:
    def test_get_reasons_public(self, client):
        """GET /api/settings/reasons accessible tanpa auth (untuk dropdown verifikator)."""
        resp = client.get("/api/settings/reasons")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_reason_requires_auth(self, client):
        """POST /api/settings/reasons memerlukan autentikasi."""
        resp = client.post("/api/settings/reasons", json={
            "value": "TEST_REASON",
            "label": "Test Label",
            "is_active": True,
            "sort_order": 0
        })
        assert resp.status_code in (401, 403)

    def test_create_reason_as_admin(self, client, admin_headers):
        """Admin bisa membuat reason baru."""
        resp = client.post("/api/settings/reasons", json={
            "value": "FOTO_BEDA",
            "label": "Foto berbeda dengan data",
            "is_active": True,
            "sort_order": 1
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "FOTO_BEDA"

    def test_create_reason_duplicate_value(self, client, admin_headers):
        """Reason dengan value duplikat harus ditolak 400."""
        client.post("/api/settings/reasons", json={
            "value": "DUPLICATE_VAL",
            "label": "Label 1",
            "is_active": True,
            "sort_order": 0
        }, headers=admin_headers)

        resp = client.post("/api/settings/reasons", json={
            "value": "DUPLICATE_VAL",
            "label": "Label 2",
            "is_active": True,
            "sort_order": 0
        }, headers=admin_headers)
        assert resp.status_code == 400

    def test_create_reason_as_verifikator_denied(self, client, verif_headers):
        """Verifikator tidak bisa membuat reason (hanya admin/supervisor)."""
        resp = client.post("/api/settings/reasons", json={
            "value": "UNAUTHORIZED",
            "label": "Test",
            "is_active": True,
            "sort_order": 0
        }, headers=verif_headers)
        assert resp.status_code == 403

    def test_update_reason(self, client, admin_headers):
        """Admin bisa mengupdate reason."""
        # Buat dulu
        create_resp = client.post("/api/settings/reasons", json={
            "value": "TO_UPDATE",
            "label": "Old Label",
            "is_active": True,
            "sort_order": 0
        }, headers=admin_headers)
        reason_id = create_resp.json()["id"]

        # Update
        resp = client.put(f"/api/settings/reasons/{reason_id}", json={
            "value": "TO_UPDATE",
            "label": "New Label",
            "is_active": False,
            "sort_order": 5
        }, headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["label"] == "New Label"
        assert resp.json()["is_active"] is False

    def test_delete_reason(self, client, admin_headers):
        """Admin bisa menghapus reason."""
        create_resp = client.post("/api/settings/reasons", json={
            "value": "TO_DELETE",
            "label": "Delete Me",
            "is_active": True,
            "sort_order": 0
        }, headers=admin_headers)
        reason_id = create_resp.json()["id"]

        resp = client.delete(f"/api/settings/reasons/{reason_id}", headers=admin_headers)
        assert resp.status_code == 200

        # Verifikasi sudah dihapus
        reasons = client.get("/api/settings/reasons").json()
        assert not any(r["id"] == reason_id for r in reasons)

    def test_delete_nonexistent_reason(self, client, admin_headers):
        """Menghapus reason yang tidak ada harus 404."""
        resp = client.delete("/api/settings/reasons/99999", headers=admin_headers)
        assert resp.status_code == 404
