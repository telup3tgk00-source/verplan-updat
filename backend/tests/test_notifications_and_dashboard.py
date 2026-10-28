"""
test_notifications_and_dashboard.py — Test /api/notifications/* dan /api/dashboard/*
"""

import pytest


class TestNotifications:
    def test_get_notifications_requires_auth(self, client):
        """GET notifications memerlukan autentikasi."""
        resp = client.get("/api/notifications/")
        assert resp.status_code in (401, 403)

    def test_get_notifications_as_verifikator(self, client, verif_headers, verifikator_user):
        """Verifikator mendapat notifikasi miliknya saja."""
        resp = client.get("/api/notifications/", headers=verif_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_unread_count(self, client, verif_headers):
        """Endpoint unread-count harus mengembalikan integer."""
        resp = client.get("/api/notifications/unread-count", headers=verif_headers)
        assert resp.status_code == 200
        assert "count" in resp.json()
        assert isinstance(resp.json()["count"], int)

    def test_mark_notification_read(self, client, verif_headers, db, verifikator_user):
        """PATCH notifikasi harus menandai sebagai sudah dibaca."""
        from app.models import Notification
        notif = Notification(
            user_id=verifikator_user.id,
            title="Test Notif",
            message="Ini pesan test",
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        resp = client.patch(f"/api/notifications/{notif.id}/read", headers=verif_headers)
        assert resp.status_code == 200

        # Verifikasi sudah dibaca
        db.expire_all()
        notif_updated = db.query(Notification).filter_by(id=notif.id).first()
        assert notif_updated.is_read is True

    def test_mark_other_user_notification(self, client, verif_headers, db, admin_user):
        """User tidak bisa menandai notifikasi milik user lain."""
        from app.models import Notification
        notif = Notification(
            user_id=admin_user.id,
            title="Admin Notif",
            message="Notif admin",
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        # Verifikator coba mark notif milik admin
        resp = client.patch(f"/api/notifications/{notif.id}/read", headers=verif_headers)
        assert resp.status_code == 404  # Tidak ditemukan untuk user ini

    def test_mark_nonexistent_notification(self, client, verif_headers):
        """Mark notifikasi yang tidak ada harus 404."""
        resp = client.patch("/api/notifications/99999/read", headers=verif_headers)
        assert resp.status_code == 404

    def test_notifications_isolation(self, client, admin_headers, verif_headers, db, admin_user, verifikator_user):
        """
        Notifikasi harus terisolasi — user A tidak bisa melihat notifikasi user B.
        """
        from app.models import Notification
        # Buat notif untuk admin
        db.add(Notification(user_id=admin_user.id, title="Admin Only", message="Secret"))
        db.commit()

        # Verifikator tidak boleh melihat notif admin
        verif_resp = client.get("/api/notifications/", headers=verif_headers)
        verif_notifs = verif_resp.json()
        admin_notif_ids = {n["title"] for n in verif_notifs}
        assert "Admin Only" not in admin_notif_ids


class TestDashboard:
    def test_dashboard_stats_no_auth(self, client):
        """
        BUG MEDIUM: /api/dashboard/stats accessible tanpa autentikasi.
        """
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200  # Dokumentasi bug

    def test_dashboard_stats_structure(self, client):
        """Dashboard stats harus mengembalikan struktur yang benar."""
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = ["total", "pending", "verified_ok", "verified_reject",
                        "need_investigation", "anomaly", "progress_pct", "chart_data"]
        for key in required_keys:
            assert key in data, f"Key '{key}' tidak ada di response dashboard"

    def test_dashboard_chart_data_is_list(self, client):
        """chart_data harus berupa list."""
        resp = client.get("/api/dashboard/stats")
        assert isinstance(resp.json()["chart_data"], list)

    def test_dashboard_progress_pct_bounds(self, client, sample_record):
        """progress_pct harus antara 0 dan 100."""
        resp = client.get("/api/dashboard/stats")
        pct = resp.json()["progress_pct"]
        assert 0 <= pct <= 100

    def test_dashboard_no_division_by_zero(self, client):
        """Dashboard tidak boleh crash ketika tidak ada data (pembagian dengan 0)."""
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0
        assert resp.json()["progress_pct"] == 0 or resp.json()["total"] > 0
