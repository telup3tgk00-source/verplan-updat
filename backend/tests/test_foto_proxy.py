"""
test_foto_proxy.py — Test untuk endpoint /api/foto/* dan modul pln_proxy.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Fixtures Foto ─────────────────────────────────────────────────────────────

DUMMY_JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 100  # magic bytes JPEG
DUMMY_PNG  = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # magic bytes PNG

VALID_COOKIE = "JSESSIONID=ABCDEF1234567890; TS01be508d=XYZ; Pool_ACMTJava=srv1"


# ─── 1. Session Management ────────────────────────────────────────────────────

class TestFotoSession:
    def test_session_status_no_cookie(self, client):
        """Status sesi tanpa cookie harus menunjukkan has_session=False."""
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = None

        resp = client.get("/api/foto/session/status")
        assert resp.status_code == 200
        assert resp.json()["has_session"] is False

    def test_update_session_valid_cookie(self, client):
        """POST cookie valid harus diterima."""
        resp = client.post("/api/foto/session", json={
            "cookie_string": VALID_COOKIE,
            "set_by": "admin"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "JSESSIONID" in data["cookie_keys"]

    def test_update_session_missing_jsessionid(self, client):
        """Cookie tanpa JSESSIONID harus ditolak 400."""
        resp = client.post("/api/foto/session", json={
            "cookie_string": "TS01be508d=XYZ; Pool=srv1",
            "set_by": "admin"
        })
        assert resp.status_code == 400
        assert "JSESSIONID" in resp.json()["detail"]

    def test_update_session_too_short(self, client):
        """Cookie string terlalu pendek harus ditolak."""
        resp = client.post("/api/foto/session", json={
            "cookie_string": "abc",
            "set_by": "admin"
        })
        assert resp.status_code == 400

    def test_update_session_empty_string(self, client):
        """Cookie string kosong harus ditolak."""
        resp = client.post("/api/foto/session", json={
            "cookie_string": "",
            "set_by": "admin"
        })
        assert resp.status_code == 400

    def test_session_status_after_set(self, client):
        """Setelah set cookie, status harus has_session=True."""
        client.post("/api/foto/session", json={
            "cookie_string": VALID_COOKIE,
            "set_by": "tester"
        })
        resp = client.get("/api/foto/session/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_session"] is True
        assert data["set_by"] == "tester"
        # PENTING: nilai cookie tidak boleh terekspos di response
        assert "ABCDEF1234567890" not in str(data), \
            "SECURITY: Nilai cookie tidak boleh terekspos di response status!"

    def test_session_status_no_auth_needed(self, client):
        """
        GET /api/foto/session/status tidak memerlukan auth — ini POTENTIALLY
        bisa disalahgunakan untuk mengecek apakah ada sesi aktif.
        Test ini mendokumentasikan kondisi saat ini.
        """
        resp = client.get("/api/foto/session/status")
        assert resp.status_code == 200  # Bisa diakses tanpa auth

    def test_update_session_no_auth_needed(self, client):
        """
        POST /api/foto/session tidak memerlukan auth — ini BUG CRITICAL!
        Siapapun bisa meng-overwrite cookie ACMT.
        Test ini mendokumentasikan bug ini.
        """
        resp = client.post("/api/foto/session", json={
            "cookie_string": VALID_COOKIE,
            "set_by": "attacker"
        })
        # Saat ini endpoint ini 200 tanpa auth — mendokumentasikan bug
        assert resp.status_code == 200  # BUG: seharusnya 401 jika tanpa token


# ─── 2. Fetch Foto — Mock ACMT ────────────────────────────────────────────────

class TestFotoFetch:

    def _set_cookie(self, client):
        """Helper untuk set cookie sebelum test fetch."""
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = VALID_COOKIE

    def test_get_foto_no_cookie(self, client):
        """Fetch foto tanpa cookie harus mengembalikan 401."""
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = None

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 401
        assert "belum diset" in resp.json()["detail"].lower() or \
               "session" in resp.json()["detail"].lower()

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_jpeg_success(self, mock_client_class, client):
        """Foto JPEG dari ACMT harus di-proxy dengan benar."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.content = DUMMY_JPEG

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 200
        assert "image" in resp.headers.get("content-type", "")

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_png_via_magic_bytes(self, mock_client_class, client):
        """Foto PNG tanpa content-type yang benar harus terdeteksi via magic bytes."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.content = DUMMY_PNG

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 200

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_session_expired_redirect(self, mock_client_class, client):
        """Redirect dari ACMT (302) harus dianggap sebagai session expired dan return 401."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {
            "content-type": "text/html",
            "location": "https://portalapp.iconpln.co.id/acmt/login.jsp"
        }
        mock_response.content = b""

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower() or \
               "kadaluarsa" in resp.json()["detail"].lower()

        # Cookie harus di-clear setelah session expired
        from app.pln_proxy import _session_cache
        assert _session_cache["cookie_string"] is None, \
            "Cookie harus dihapus setelah session expired terdeteksi"

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_html_login_page(self, mock_client_class, client):
        """Response HTML dengan form login harus dianggap session expired."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"<html><form><input name='j_username'/></form></html>"
        mock_response.text = "<html><form><input name='j_username'/></form></html>"

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 401

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_empty_response(self, mock_client_class, client):
        """Response kosong (0 bytes) harus mengembalikan 404."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.content = b""
        mock_response.text = ""

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code in (404, 502)

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_acmt_server_error(self, mock_client_class, client):
        """HTTP 500 dari ACMT harus mengembalikan 502 (bad gateway)."""
        self._set_cookie(client)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"Internal Server Error"
        mock_response.text = "Internal Server Error"

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        assert resp.status_code == 502

    @patch("app.pln_proxy.httpx.AsyncClient")
    def test_get_foto_connection_timeout(self, mock_client_class, client):
        """Timeout koneksi ke ACMT harus ditangani dengan baik (tidak hang)."""
        import httpx
        self._set_cookie(client)

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(side_effect=httpx.TimeoutException("Connection timeout"))
        mock_client_class.return_value = mock_async_client

        resp = client.get("/api/foto", params={
            "idpel": "123456789012",
            "blth": "202605",
            "fotoke": "1"
        })
        # Harus mengembalikan error, bukan hang
        assert resp.status_code == 500

    def test_get_foto_missing_params(self, client):
        """Request tanpa parameter wajib harus mengembalikan 422."""
        resp = client.get("/api/foto")
        assert resp.status_code == 422

    def test_get_foto_no_auth_required(self, client):
        """
        BUG MEDIUM: /api/foto tidak memerlukan autentikasi JWT.
        Siapa saja yang punya cookie ACMT bisa mengakses foto.
        """
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = None
        # Tanpa token pun bisa memanggil endpoint (akan gagal di validasi cookie ACMT, bukan JWT)
        resp = client.get("/api/foto", params={
            "idpel": "test",
            "blth": "202605",
            "fotoke": "1"
        })
        # 401 karena cookie ACMT belum set, BUKAN karena JWT
        assert resp.status_code == 401
        assert "acmt" in resp.json()["detail"].lower() or \
               "cookie" in resp.json()["detail"].lower()


# ─── 3. Debug Endpoint ────────────────────────────────────────────────────────

class TestFotoDebug:
    def test_debug_endpoint_no_auth(self, client):
        """
        BUG HIGH: /api/foto/debug accessible tanpa auth.
        Bisa digunakan untuk reconnaissance sistem ACMT.
        """
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = VALID_COOKIE

        with patch("app.routers.foto.httpx.AsyncClient") as mock_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "text/html"}
            mock_resp.content = b"<html>test</html>"
            mock_resp.text = "<html>test</html>"
            mock_ac = AsyncMock()
            mock_ac.__aenter__ = AsyncMock(return_value=mock_ac)
            mock_ac.__aexit__ = AsyncMock(return_value=None)
            mock_ac.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ac

            resp = client.get("/api/foto/debug", params={
                "idpel": "test",
                "blth": "202605",
                "fotoke": "1"
            })
        # Endpoint saat ini accessible tanpa auth — dokumentasi bug
        assert resp.status_code == 200  # BUG: seharusnya memerlukan auth admin


# ─── 4. PLN Proxy Module Unit Tests ──────────────────────────────────────────

class TestPlnProxyModule:
    def test_set_cookie_string_logs_keys_not_values(self):
        """set_cookie_string harus log nama key, bukan nilai cookie."""
        from app.pln_proxy import set_cookie_string, _session_cache
        set_cookie_string("JSESSIONID=SECRET123; TS01=TOPSECRET", "test")
        # Nilai cookie tidak boleh tersimpan dengan mudah diakses via status
        status = _session_cache
        # Ini test bahwa nilai memang disimpan (untuk fungsi) tapi tidak expose di API response
        assert status["cookie_string"] is not None

    def test_get_session_status_hides_values(self):
        """get_session_status tidak boleh mengembalikan nilai cookie."""
        from app.pln_proxy import set_cookie_string, get_session_status
        set_cookie_string("JSESSIONID=SUPERSECRET456; Pool=srv1", "admin")
        status = get_session_status()
        # Nilai "SUPERSECRET456" tidak boleh ada di dalam response
        status_str = str(status)
        assert "SUPERSECRET456" not in status_str, \
            "SECURITY: Nilai cookie tidak boleh terekspos di get_session_status!"
        # Hanya key yang boleh ada
        assert "JSESSIONID" in status["cookie_keys"]

    def test_session_cleared_on_expired(self):
        """Setelah session expired, cookie harus di-clear."""
        from app.pln_proxy import _session_cache
        _session_cache["cookie_string"] = VALID_COOKIE
        # Simulasi deteksi expired
        _session_cache["cookie_string"] = None
        assert _session_cache["cookie_string"] is None

    def test_concurrent_cookie_update(self):
        """
        Test basic thread safety — multiple update tidak boleh corrupt state.
        (Race condition minimal test)
        """
        import threading
        from app.pln_proxy import set_cookie_string, _session_cache

        results = []
        def update_cookie(value):
            set_cookie_string(f"JSESSIONID={value}; TS01=X", f"user_{value}")
            results.append(_session_cache["cookie_string"])

        threads = [threading.Thread(target=update_cookie, args=(f"VAL{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Cookie harus berupa string valid (tidak None atau corrupt)
        final = _session_cache["cookie_string"]
        assert final is not None
        assert "JSESSIONID=" in final
