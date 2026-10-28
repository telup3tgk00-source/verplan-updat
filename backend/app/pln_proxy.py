"""
PLN ACMT Proxy Module — Dual Mode (ACMT Lama & ACMT New)
Mendukung pengambilan foto dari:
1. ACMT Lama (Cookie session / portalapp.iconpln.co.id)
2. ACMT New (Bearer JWT token / API 121.100.23.228:8030)
3. Auto mode: Mendukung prioritas 'new_first' (untuk wilayah migrasi New) atau 'lama_first'
"""

import os
import re
import json
import logging
import asyncio
import threading
import queue
import base64
import time
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# Pre-configured limits
_ACMT_LIMITS = httpx.Limits(max_keepalive_connections=15, max_connections=30)
_ACMT_TIMEOUT = httpx.Timeout(connect=15.0, read=25.0, write=15.0, pool=15.0)

# URL ACMT Lama
ACMT_BASE_URL = "https://portalapp.iconpln.co.id/acmt"
PHOTO_URL     = f"{ACMT_BASE_URL}/DisplayBlobServlet1"

# URL ACMT New
URL_ACMT_NEW_API = os.getenv("URL_ACMT_NEW_API", "http://121.100.23.228:8030")
URL_ACMT_NEW_WEB = os.getenv("URL_ACMT_NEW_WEB", "http://121.100.23.228:8088")

# Path file persistensi sesi ACMT New & ACMT Lama
SESSION_NEW_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "session_new.json")
SESSION_LAMA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "session_lama.json")

# ─── Sesi ACMT Lama (Cookie in-memory & file persistensi) ─────────────────────
_session_cache: dict = {
    "cookie_string": None,   # full cookie string dari browser
    "set_by":        None,
    "set_at":        None,
}

# ─── Sesi ACMT New (JWT Bearer token) ──────────────────────────────────────────
_session_new_cache: dict = {
    "token":         None,   # JWT Bearer Token (diisi otomatis saat login / sync)
    "username":      None,   # Username akun ACMT New (diisi otomatis saat login / sync)
    "unitup":        None,   # Kode Unit UP PLN (diisi otomatis saat login / sync)
    "priority":      "new_first",  # 'new_first' (default untuk wilayah migrasi) | 'lama_first'
    "set_by":        None,
    "set_at":        None,
}

_BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": f"{ACMT_BASE_URL}/Main.html",
}

# Load sesi ACMT New jika ada file tersimpan
def _load_persisted_session_new():
    candidates = [
        SESSION_NEW_FILE,
        os.path.join(os.path.dirname(SESSION_NEW_FILE), "uploads", "session_new.json"),
        os.path.join(os.path.dirname(os.path.dirname(SESSION_NEW_FILE)), "session_new.json")
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and (data.get("token") or data.get("username")):
                        _session_new_cache.update(data)
                        logger.info("Loaded persisted ACMT New session from %s: username=%s", path, data.get("username"))
                        break
            except Exception as e:
                logger.warning("Gagal memuat %s: %s", path, e)

_load_persisted_session_new()


# Smart Parser untuk Cookie ACMT Lama (Mendukung format string biasa, JSON array, JSON object, dsb)
def parse_cookie_input(raw: str) -> str:
    """
    Otomatis membedah input baik berupa:
    - String biasa: 'JSESSIONID=xxx; Pool_ACMTJava=yyy'
    - JSON Array: '[{"name": "JSESSIONID", "value": "..."}, ...]'
    - JSON Object: '{"JSESSIONID": "...", "Pool_ACMTJava": "..."}' atau '{"cookies": [...]}'
    - Raw JSESSIONID value: '81EA7996...'
    """
    cleaned = (raw or "").strip()
    if not cleaned:
        return ""

    # Cek jika format JSON
    if (cleaned.startswith("[") and cleaned.endswith("]")) or (cleaned.startswith("{") and cleaned.endswith("}")):
        try:
            parsed = json.loads(cleaned)
            # Format list of cookie objects [{"name": "JSESSIONID", "value": "..."}, ...]
            if isinstance(parsed, list):
                parts = [f"{c['name']}={c['value']}" for c in parsed if isinstance(c, dict) and "name" in c and "value" in c]
                if parts:
                    return "; ".join(parts)
            # Format dict {"cookies": [...]}
            elif isinstance(parsed, dict):
                if "cookie_string" in parsed and isinstance(parsed["cookie_string"], str):
                    return parsed["cookie_string"].strip()
                if "cookies" in parsed and isinstance(parsed["cookies"], list):
                    parts = [f"{c['name']}={c['value']}" for c in parsed["cookies"] if isinstance(c, dict) and "name" in c and "value" in c]
                    if parts:
                        return "; ".join(parts)
                # Format key-value {"JSESSIONID": "...", "Pool_ACMTJava": "..."}
                parts = [f"{k}={v}" for k, v in parsed.items() if isinstance(v, str) and not k.startswith("_")]
                if parts:
                    return "; ".join(parts)
        except Exception:
            pass

    # Jika user hanya paste heksadesimal JSESSIONID tanpa 'JSESSIONID='
    if "=" not in cleaned and len(cleaned) >= 16:
        return f"JSESSIONID={cleaned}"

    return cleaned


def check_acmt_lama_cookie_live(cookie_string: str) -> bool:
    """Cek secara real-time apakah cookie ACMT Lama aktif (merespon 200 di Main.html) atau 302 ke Ipam.html."""
    if not cookie_string or "JSESSIONID" not in cookie_string:
        return False
    try:
        with httpx.Client(timeout=6.0, verify=False, follow_redirects=False) as client:
            resp = client.get(
                f"{ACMT_BASE_URL}/Main.html",
                headers={**_BASE_HEADERS, "Cookie": cookie_string}
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location", "").lower()
                if "ipam" in loc or "login" in loc:
                    return False
            return resp.status_code == 200
    except Exception as e:
        logger.debug("check_acmt_lama_cookie_live error: %s", e)
        return False


# Load sesi ACMT Lama jika ada file tersimpan
def _load_persisted_session_lama():
    candidates = [
        SESSION_LAMA_FILE,
        os.path.join(os.path.dirname(SESSION_LAMA_FILE), "uploads", "session_lama.json"),
        os.path.join(os.path.dirname(os.path.dirname(SESSION_LAMA_FILE)), "session_lama.json"),
        os.path.join(os.path.dirname(os.path.dirname(SESSION_LAMA_FILE)), "session.json")
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    cookie_str = parse_cookie_input(content)
                    if cookie_str and "JSESSIONID" in cookie_str:
                        if check_acmt_lama_cookie_live(cookie_str):
                            _session_cache["cookie_string"] = cookie_str
                            _session_cache["set_by"] = "persisted_file"
                            _session_cache["set_at"] = datetime.now().isoformat()
                            logger.info("Loaded live persisted ACMT Lama session from %s", path)
                            break
                        else:
                            # Tetap gunakan cookie yang tersimpan sebagai best effort
                            _session_cache["cookie_string"] = cookie_str
                            _session_cache["set_by"] = "persisted_file"
                            _session_cache["set_at"] = datetime.now().isoformat()
                            logger.info("Loaded persisted ACMT Lama session from %s (live check pending)", path)
                            break
            except Exception as e:
                logger.warning("Gagal memuat %s: %s", path, e)

_load_persisted_session_lama()


# ─── Handler ACMT Lama ────────────────────────────────────────────────────────

def set_cookie_string(cookie_string: str, set_by: str = "admin") -> None:
    """Simpan full cookie string dari browser untuk ACMT Lama dan persistensikan ke file."""
    cleaned = parse_cookie_input(cookie_string)
    _session_cache["cookie_string"] = cleaned
    _session_cache["set_by"]        = set_by
    _session_cache["set_at"]        = datetime.now().isoformat()
    keys = [part.split("=")[0].strip() for part in cleaned.split(";") if "=" in part]

    # Simpan permanen ke session_lama.json
    try:
        with open(SESSION_LAMA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "cookie_string": cleaned,
                "set_by": set_by,
                "set_at": _session_cache["set_at"],
                "cookie_keys": keys
            }, f, indent=2)
        logger.info("Sesi ACMT Lama berhasil disimpan ke %s", SESSION_LAMA_FILE)
    except Exception as e:
        logger.warning("Gagal menyimpan %s: %s", SESSION_LAMA_FILE, e)

    logger.info("Cookie ACMT Lama diupdate oleh %s -> keys: %s", set_by, ", ".join(keys))


# ─── Handler ACMT New ─────────────────────────────────────────────────────────

def set_token_new(token: str, username: str = None, unitup: str = None, set_by: str = "admin") -> None:
    """Simpan Bearer Token JWT untuk ACMT New."""
    cleaned = token.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    _session_new_cache["token"] = cleaned
    if username:
        _session_new_cache["username"] = username.strip()
    if unitup:
        _session_new_cache["unitup"] = unitup.strip()
    _session_new_cache["set_by"] = set_by
    _session_new_cache["set_at"] = datetime.now().isoformat()

    try:
        with open(SESSION_NEW_FILE, "w", encoding="utf-8") as f:
            json.dump(_session_new_cache, f, indent=2)
    except Exception as e:
        logger.warning("Gagal menyimpan session_new.json: %s", e)

    logger.info("Token ACMT New diupdate oleh %s (user: %s, unitup: %s)", set_by, _session_new_cache.get("username"), _session_new_cache.get("unitup"))


def set_priority(priority: str) -> str:
    """Mengatur prioritas pencarian foto: 'new_first' atau 'lama_first'."""
    p = (priority or "new_first").lower().strip()
    if p not in ("new_first", "lama_first"):
        p = "new_first"
    _session_new_cache["priority"] = p
    try:
        with open(SESSION_NEW_FILE, "w", encoding="utf-8") as f:
            json.dump(_session_new_cache, f, indent=2)
    except Exception as e:
        logger.warning("Gagal menyimpan priority ke session_new.json: %s", e)
    logger.info("Prioritas server foto diubah menjadi: %s", p)
    return p


async def login_acmt_new(username: str, password: str, enkripsi: str = "", unitup: str = "") -> dict:
    """Melakukan login langsung ke API ACMT New untuk mendapatkan Bearer Token."""
    url = f"{URL_ACMT_NEW_API}/acmt/v1/auth/login"
    payload = {
        "username": username.strip(),
        "password": password.strip(),
        "tokenInfo": enkripsi.strip() if enkripsi else ""
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": _BASE_HEADERS["User-Agent"]
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            resp = await client.post(url, json=payload, headers=headers)
            res_json = resp.json()
            if not res_json.get("success"):
                return {
                    "ok": False,
                    "message": res_json.get("message", "Login gagal: periksa Username/Password/Enkripsi")
                }
            data_obj = res_json.get("data", {})
            token = data_obj.get("token", "")
            if not token:
                return {"ok": False, "message": "Server ACMT tidak mengembalikan token"}

            resolved_unitup = unitup.strip() if unitup else (username.split('.')[0] if '.' in username else username[:5])
            set_token_new(token=token, username=username.strip(), unitup=resolved_unitup, set_by="direct-login")
            return {
                "ok": True,
                "message": f"Login ACMT New berhasil! Terhubung sebagai {username}",
                "unitup": resolved_unitup,
                "token_preview": token[:15] + "..."
            }
    except Exception as e:
        logger.exception("Error login ACMT New")
        return {"ok": False, "message": f"Gagal menghubungi server ACMT New: {str(e)}"}


# ─── Status Sesi ──────────────────────────────────────────────────────────────

def get_session_status() -> dict:
    """Mengembalikan status sesi ACMT Lama dan ACMT New serta prioritas aktif."""
    cookie_string = _session_cache.get("cookie_string")
    keys = []
    if cookie_string:
        keys = [p.split("=")[0].strip() for p in cookie_string.split(";") if "=" in p]

    has_lama = bool(cookie_string)
    token_new = _session_new_cache.get("token")
    has_new = bool(token_new)
    active_priority = _session_new_cache.get("priority", "new_first")

    return {
        # Backward compatibility fields (tetap ada agar frontend lama tidak rusak)
        "has_session": has_lama or has_new,
        "priority":    active_priority,
        "set_by":      _session_cache.get("set_by") or _session_new_cache.get("set_by"),
        "set_at":      _session_cache.get("set_at") or _session_new_cache.get("set_at"),
        "cookie_keys": keys,

        # Detail kedua sistem
        "acmt_lama": {
            "has_session": has_lama,
            "set_by":      _session_cache.get("set_by"),
            "set_at":      _session_cache.get("set_at"),
            "cookie_keys": keys,
        },
        "acmt_new": {
            "has_session": has_new,
            "username":    _session_new_cache.get("username"),
            "unitup":      _session_new_cache.get("unitup"),
            "priority":    active_priority,
            "set_by":      _session_new_cache.get("set_by"),
            "set_at":      _session_new_cache.get("set_at"),
            "token_preview": (token_new[:15] + "...") if token_new else None
        }
    }


# ─── Fetch ACMT Lama ──────────────────────────────────────────────────────────

async def fetch_photo(idpel: str, blth: str, fotoke: str, client_cookie: str = None, unitup: str = None) -> tuple[bytes, str]:
    """
    Ambil foto meter dari ACMT PLN Lama (DisplayBlobServlet1).
    """
    cookie_string = client_cookie or _session_cache.get("cookie_string")
    
    if not cookie_string:
        raise RuntimeError(
            "Cookie ACMT belum diset. Pastikan Ekstensi Chrome Metrik berjalan atau hubungkan sesi ACMT Lama."
        )

    eff_unitup = unitup or (idpel[:5] if len(idpel) >= 5 else "")

    params = {
        "idpel":       idpel,
        "nomor_meter": "null",
        "fotoke":      fotoke,
        "blth":        blth,
        "isPhoto":     "null",
    }

    headers = {
        **_BASE_HEADERS,
        "Cookie": cookie_string,
    }

    async with httpx.AsyncClient(
        timeout=_ACMT_TIMEOUT,
        limits=_ACMT_LIMITS,
        verify=False,
        follow_redirects=False,
    ) as client:
        resp = await client.get(PHOTO_URL, params=params, headers=headers)

    # Tangkap rotasi cookie
    if resp.cookies:
        current_cookies = {}
        for pair in cookie_string.split(";"):
            if "=" in pair:
                k, v = pair.strip().split("=", 1)
                current_cookies[k] = v
        
        updated = False
        for k, v in resp.cookies.items():
            if current_cookies.get(k) != v:
                current_cookies[k] = v
                updated = True
        
        if updated:
            new_cookie_string = "; ".join(f"{k}={v}" for k, v in current_cookies.items())
            _session_cache["cookie_string"] = new_cookie_string

    content_type = resp.headers.get("content-type", "").lower()
    status_code  = resp.status_code

    if status_code == 200 and len(resp.content) > 0 and (
        content_type.startswith("image/")
        or content_type == "application/octet-stream"
    ):
        ct = content_type if content_type.startswith("image/") else "image/jpeg"
        return resp.content, ct

    if status_code == 200 and len(resp.content) > 100:
        if resp.content[:3] == b'\xff\xd8\xff':
            return resp.content, "image/jpeg"
        if resp.content[:4] == b'\x89PNG':
            return resp.content, "image/png"

    if status_code in (301, 302, 303, 307, 308):
        loc = resp.headers.get("location", "").lower()
        if "ipam" in loc or "login" in loc:
            raise RuntimeError("SESSION_EXPIRED: ACMT merespon Redirect ke Ipam (sesi ACMT Lama kedaluwarsa).")
        raise RuntimeError(f"Foto tidak tersedia (redirect ke {loc})")

    if status_code >= 500:
        raise RuntimeError(f"Server ACMT Error (HTTP {status_code})")

    if "text/html" in content_type or status_code in (401, 403):
        body = resp.text[:400] if resp.content else ""
        if any(k in body.lower() for k in ("login", "captcha", "j_username", "ipam")):
            raise RuntimeError("SESSION_EXPIRED: Cookie ACMT sudah kadaluarsa.")
        raise RuntimeError(f"Foto tidak tersedia (idpel={idpel} blth={blth} fotoke={fotoke})")

    if status_code == 200 and len(resp.content) == 0:
        raise RuntimeError(f"Foto tidak tersedia — response kosong (idpel={idpel} blth={blth} fotoke={fotoke})")

    raise RuntimeError(f"Gagal mengambil foto: HTTP {status_code} ct={content_type}")


# ─── Fetch ACMT New ───────────────────────────────────────────────────────────

async def fetch_photo_new(
    idpel: str, 
    blth: str, 
    fotoke: str = "1", 
    client_token: str = None, 
    unitup: str = None
) -> tuple[bytes, str]:
    """
    Ambil foto meter dari ACMT New API (infopelanggan / histopelprabayar -> photo/meternfs).
    """
    token = client_token or _session_new_cache.get("token")
    if not token:
        raise RuntimeError("Token ACMT New belum diset. Silakan hubungkan sesi ACMT New.")

    auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
    eff_username = _session_new_cache.get("username") or ""
    eff_unitup = unitup or _session_new_cache.get("unitup") or (eff_username.split('.')[0] if '.' in eff_username else (eff_username[:5] if eff_username else ""))

    payload = {
        "idpel": idpel.strip(),
        "unitup": eff_unitup,
        "transaksiby": eff_username
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth_header,
        "User-Agent": _BASE_HEADERS["User-Agent"]
    }

    primary_url = f"{URL_ACMT_NEW_API}/acmt/informasi/infopelanggan"
    fallback_url = f"{URL_ACMT_NEW_API}/acmt/informasi/histopelprabayar"

    json_data = None
    async with httpx.AsyncClient(timeout=15.0, limits=_ACMT_LIMITS, verify=False) as client:
        # Coba pascabayar
        try:
            resp = await client.post(primary_url, json=payload, headers=headers)
            if resp.status_code == 200:
                json_data = resp.json()
            elif resp.status_code in (401, 403):
                _session_new_cache["token"] = None
                raise RuntimeError("SESSION_EXPIRED: Token ACMT New sudah kedaluwarsa.")
        except httpx.HTTPError as exc:
            logger.warning("Request primary ACMT New gagal: %s", exc)

        # Coba prabayar jika data kosong
        data_records = json_data.get("data") if json_data and isinstance(json_data, dict) else []
        if not data_records:
            try:
                resp_alt = await client.post(fallback_url, json=payload, headers=headers)
                if resp_alt.status_code == 200:
                    json_data = resp_alt.json()
                    data_records = json_data.get("data") if json_data and isinstance(json_data, dict) else []
                elif resp_alt.status_code in (401, 403):
                    _session_new_cache["token"] = None
                    raise RuntimeError("SESSION_EXPIRED: Token ACMT New sudah kedaluwarsa.")
            except httpx.HTTPError as exc:
                logger.warning("Request fallback ACMT New gagal: %s", exc)

        if not data_records:
            raise RuntimeError(f"Data pelanggan {idpel} tidak ditemukan di ACMT New.")

        # Cari data record yang sesuai dengan blth
        target_record = None
        for rec in data_records:
            if str(rec.get("blth", "")).strip() == str(blth).strip():
                target_record = rec
                break

        # Kumpulkan foto yang tersedia
        photo_urls = []
        if target_record:
            path_foto = target_record.get("pathFoto")
            if isinstance(path_foto, list):
                for p_obj in path_foto:
                    if isinstance(p_obj, dict):
                        for k in ["photo1", "photo2", "photo3", "path"]:
                            u = p_obj.get(k)
                            if u and isinstance(u, str):
                                photo_urls.append(u.strip())
            elif isinstance(path_foto, str) and path_foto.strip():
                photo_urls.append(path_foto.strip())

        # Regex fallback jika pathFoto tidak spesifik
        if not photo_urls:
            raw_text = json.dumps(target_record if target_record else data_records)
            pola_full = r'(\d{5}/\d{6}/\d{6}_[^"\'\s/]+\.(?:jpg|jpeg|png))'
            pola_file = r'(\d{6}_[^"\'\s/]+\.(?:jpg|jpeg|png))'
            matches = list(dict.fromkeys(re.findall(pola_full, raw_text, re.I) + re.findall(pola_file, raw_text, re.I)))
            matches_blth = [m for m in matches if str(blth) in m]
            photo_urls = matches_blth if matches_blth else matches

        if not photo_urls:
            raise RuntimeError(f"Foto tidak tersedia di ACMT New (idpel={idpel} blth={blth} fotoke={fotoke})")

        # Tentukan urutan foto sesuai fotoke
        try:
            fk_idx = max(0, int(fotoke) - 1)
        except (ValueError, TypeError):
            fk_idx = 0
        
        selected_photo_path = photo_urls[fk_idx] if fk_idx < len(photo_urls) else photo_urls[0]

        # Susun alternatif URL unduhan
        nama_file = selected_photo_path.split("/")[-1]
        possible_urls = []
        if selected_photo_path.startswith("http"):
            possible_urls.append(selected_photo_path)
        else:
            clean_path = selected_photo_path.lstrip("/")
            possible_urls.extend([
                f"{URL_ACMT_NEW_API}/acmt/download/photo/meternfs/{clean_path}",
                f"{URL_ACMT_NEW_API}/acmt/download/photo/meter/{clean_path}",
                f"{URL_ACMT_NEW_API}/acmt/download/photo/meternfs/{eff_unitup}/{blth}/{nama_file}",
                f"{URL_ACMT_NEW_API}/acmt/download/photo/meter/{eff_unitup}/{blth}/{nama_file}",
            ])

        headers_img = {
            "Accept": "image/*,*/*",
            "Authorization": auth_header,
            "User-Agent": _BASE_HEADERS["User-Agent"]
        }

        for img_url in possible_urls:
            try:
                r_img = await client.get(img_url, headers=headers_img, timeout=12.0)
                if r_img.status_code == 200 and len(r_img.content) > 100:
                    ct = r_img.headers.get("content-type", "")
                    if not ct.startswith("image/"):
                        if r_img.content[:3] == b'\xff\xd8\xff':
                            ct = "image/jpeg"
                        elif r_img.content[:4] == b'\x89PNG':
                            ct = "image/png"
                        else:
                            ct = "image/jpeg"
                    return r_img.content, ct
            except Exception as e:
                logger.debug("Download %s gagal: %s", img_url, e)
                continue

        raise RuntimeError(f"Gagal mengunduh file foto dari ACMT New (idpel={idpel} blth={blth} fotoke={fotoke})")


# ─── Smart Fetcher (Unified Dispatcher with Priority) ─────────────────────────

async def fetch_photo_smart(
    idpel: str,
    blth: str,
    fotoke: str,
    client_cookie: str = None,
    client_token: str = None,
    source: str = "auto",
    priority: str = None,
    unitup: str = None
) -> tuple[bytes, str, str]:
    """
    Mengambil foto secara cerdas:
    - source="lama": hanya ambil dari ACMT Lama
    - source="new": hanya ambil dari ACMT New
    - source="auto": 
        * priority="new_first" (default untuk wilayah yang sudah beralih):
          Ambil dari ACMT New dulu secara cepat. Jika foto kosong/belum ada, otomatis fallback ke ACMT Lama.
        * priority="lama_first":
          Ambil dari ACMT Lama dulu. Jika foto kosong/expired, fallback ke ACMT New.
    Mengembalikan: (image_bytes, content_type, source_used)
    """
    mode = (source or "auto").lower()

    if mode == "lama":
        content, ct = await fetch_photo(idpel=idpel, blth=blth, fotoke=fotoke, client_cookie=client_cookie, unitup=unitup)
        return content, ct, "ACMT Lama"

    if mode == "new":
        content, ct = await fetch_photo_new(idpel=idpel, blth=blth, fotoke=fotoke, client_token=client_token, unitup=unitup)
        return content, ct, "ACMT New"

    # Mode AUTO: Cek ketersediaan sesi
    has_lama = bool(client_cookie or _session_cache.get("cookie_string"))
    has_new = bool(client_token or _session_new_cache.get("token"))

    if not has_lama and not has_new:
        raise RuntimeError(
            "Sesi ACMT belum diset. Silakan hubungkan ACMT New (Token/Login) atau ACMT Lama (Cookie)."
        )

    # Tentukan prioritas (default: new_first agar wilayah yang sudah beralih tidak terkena delay)
    eff_priority = (priority or _session_new_cache.get("priority") or "new_first").lower().strip()

    # OPSI A: PRIORITAS NEW DULUAN (Rekomendasi untuk wilayah yang sudah beralih ke ACMT New)
    if eff_priority == "new_first":
        if has_new:
            try:
                content, ct = await fetch_photo_new(idpel=idpel, blth=blth, fotoke=fotoke, client_token=client_token, unitup=unitup)
                return content, ct, "ACMT New"
            except Exception as exc_new:
                logger.info("Foto di ACMT New tidak tersedia (%s). Mencoba fallback ke ACMT Lama...", exc_new)
                if has_lama:
                    try:
                        content, ct = await fetch_photo(idpel=idpel, blth=blth, fotoke=fotoke, client_cookie=client_cookie, unitup=unitup)
                        return content, ct, "ACMT Lama"
                    except Exception as exc_lama:
                        raise RuntimeError(f"Foto tidak ditemukan di ACMT New maupun ACMT Lama.")
                raise exc_new

        # Jika sesi New belum diset tapi sesi Lama ada
        content, ct = await fetch_photo(idpel=idpel, blth=blth, fotoke=fotoke, client_cookie=client_cookie, unitup=unitup)
        return content, ct, "ACMT Lama"

    # OPSI B: PRIORITAS LAMA DULUAN (Untuk wilayah yang belum migrasi)
    else:
        if has_lama:
            try:
                content, ct = await fetch_photo(idpel=idpel, blth=blth, fotoke=fotoke, client_cookie=client_cookie, unitup=unitup)
                return content, ct, "ACMT Lama"
            except Exception as exc_lama:
                logger.info("Foto ACMT Lama tidak tersedia (%s). Mencoba fallback ke ACMT New...", exc_lama)
                if has_new:
                    try:
                        content, ct = await fetch_photo_new(idpel=idpel, blth=blth, fotoke=fotoke, client_token=client_token, unitup=unitup)
                        return content, ct, "ACMT New"
                    except Exception as exc_new:
                        raise RuntimeError(f"Foto tidak ditemukan di ACMT Lama maupun ACMT New.")
                raise exc_lama

        # Jika sesi Lama belum diset tapi sesi New ada
        content, ct = await fetch_photo_new(idpel=idpel, blth=blth, fotoke=fotoke, client_token=client_token, unitup=unitup)
        return content, ct, "ACMT New"


# ─── ACMT Lama Headless Login Manager & Session Reset ─────────────────────────

def get_browser_executable():
    paths = [
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

class AcmtLamaLoginManager:
    """Manager background thread untuk headless login dan penangkapan CAPTCHA ACMT Lama (IPAM)."""
    def __init__(self):
        self.cmd_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _worker_loop(self):
        playwright = None
        browser = None
        context = None
        page = None

        def ensure_page():
            nonlocal playwright, browser, context, page
            from playwright.sync_api import sync_playwright
            browser_exe = get_browser_executable()
            if page and not page.is_closed():
                if "Ipam.html" in page.url:
                    try:
                        if page.locator("input[name='password']").is_visible():
                            return page
                    except Exception:
                        pass
                # Jika halaman berada di Main.html atau tidak sehat, bersihkan untuk sesi baru
                try: page.close()
                except Exception: pass
                page = None
                if context:
                    try: context.close()
                    except Exception: pass
                    context = None

            if not playwright:
                playwright = sync_playwright().start()
            if not browser:
                launch_kwargs = {
                    "headless": True,
                    "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-infobars"]
                }
                if browser_exe:
                    launch_kwargs["executable_path"] = browser_exe
                browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(f"{ACMT_BASE_URL}/Ipam.html", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector("input[name='password']", timeout=15000)
            return page

        while True:
            cmd, args, result_holder, done_event = self.cmd_queue.get()
            try:
                if cmd == "get_captcha":
                    refresh = args.get("refresh", False)
                    pg = ensure_page()
                    if refresh:
                        try:
                            btn_recaptcha = pg.locator("button:has-text('ReCaptcha')").first
                            if btn_recaptcha.count() > 0 and btn_recaptcha.is_visible():
                                try:
                                    with pg.expect_response(lambda r: "CaptchaServlet" in r.url, timeout=5000):
                                        btn_recaptcha.click()
                                    pg.wait_for_timeout(300)
                                except Exception:
                                    btn_recaptcha.click()
                                    pg.wait_for_timeout(1000)
                        except Exception as e_re:
                            logger.debug("[RECAPTCHA CLICK ERROR] %s", e_re)

                    try:
                        img_el = pg.locator("img[src*='CaptchaServlet']").first
                        img_el.wait_for(state="visible", timeout=5000)
                        img_bytes = img_el.screenshot(timeout=5000)
                    except Exception as e_shot:
                        logger.debug("[CAPTCHA SCREENSHOT RETRY] %s", e_shot)
                        try:
                            ok_btn = pg.locator(".x-window-dlg button:has-text('OK'), .x-window-dlg button:has-text('Ya')").first
                            if ok_btn.count() > 0 and ok_btn.is_visible():
                                ok_btn.click()
                                pg.wait_for_timeout(500)
                        except Exception:
                            pass
                        pg.goto(f"{ACMT_BASE_URL}/Ipam.html", wait_until="domcontentloaded", timeout=20000)
                        pg.wait_for_selector("input[name='password']", timeout=15000)
                        img_el = pg.locator("img[src*='CaptchaServlet']").first
                        img_el.wait_for(state="visible", timeout=6000)
                        img_bytes = img_el.screenshot(timeout=6000)

                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    result_holder["result"] = f"data:image/png;base64,{b64}"

                elif cmd == "submit_login":
                    username = args.get("username", "")
                    password = args.get("password", "")
                    captcha = args.get("captcha", "")
                    pg = ensure_page()

                    captcha_status = None
                    login_rpc_err = None

                    def handle_resp(resp):
                        nonlocal captcha_status, login_rpc_err
                        try:
                            url = resp.url
                            if "captchaService" in url:
                                txt = resp.text()
                                if "//OK[1" in txt:
                                    captcha_status = True
                                elif "//OK[0" in txt:
                                    captcha_status = False
                            elif "ipam/login" in url:
                                txt = resp.text()
                                if "Salah" in txt or "message" in txt or "tidak aktif" in txt.lower():
                                    m = re.search(r'"message"\s*,\s*"([^"]+)"', txt)
                                    if m:
                                        login_rpc_err = m.group(1)
                                    elif "Nama Pengguna Atau Kata Sandi Salah" in txt:
                                        login_rpc_err = "Nama Pengguna Atau Kata Sandi Salah"
                        except Exception:
                            pass

                    pg.on("response", handle_resp)

                    # 1. Input username
                    u_el = pg.locator("input[name='user']").first
                    u_el.click()
                    pg.keyboard.press("Control+A")
                    pg.keyboard.press("Backspace")
                    pg.keyboard.type(username, delay=10)
                    pg.keyboard.press("Tab")

                    # 2. Input password
                    p_el = pg.locator("input[name='password']").first
                    p_el.click()
                    pg.keyboard.press("Control+A")
                    pg.keyboard.press("Backspace")
                    pg.keyboard.type(password, delay=10)
                    pg.keyboard.press("Tab")

                    # 3. Input captcha
                    c_el = pg.locator("input[placeholder*='CAPTCHA'], input.gwt-TextBox").first
                    c_el.click()
                    pg.keyboard.press("Control+A")
                    pg.keyboard.press("Backspace")
                    pg.keyboard.type(captcha, delay=10)
                    pg.keyboard.press("Tab")

                    pg.wait_for_timeout(200)

                    # 4. Klik tombol Login
                    btn_login = pg.locator("button:has-text('Login')").first
                    btn_login.click(force=True)

                    # Tunggu respon atau navigasi
                    for _ in range(35):
                        pg.wait_for_timeout(300)
                        if "Main.htm" in pg.url or "Main.html" in pg.url or "Ipam.html" not in pg.url:
                            break
                        if captcha_status is False:
                            break
                        alerts = pg.locator(".ext-mb-text, .x-window-mc, .x-window-dlg").all()
                        has_popup = False
                        for a in alerts:
                            t = a.inner_text().strip()
                            if t and "Catat Meter Terpusat" not in t and "Username" not in t and "please wait" not in t.lower():
                                has_popup = True
                                break
                        if has_popup:
                            break

                    try:
                        pg.remove_listener("response", handle_resp)
                    except Exception:
                        pass

                    err_msg = ""
                    warning_msg = ""
                    is_success_dialog = False

                    alerts = pg.locator(".ext-mb-text, .x-window-mc, .x-window-dlg").all()
                    for a in alerts:
                        t = a.inner_text().strip()
                        if t and "Catat Meter Terpusat" not in t and "Username" not in t and "Login" not in t and "please wait" not in t.lower():
                            t_lower = t.lower()
                            if "sukses" in t_lower or "berhasil" in t_lower or "success" in t_lower:
                                is_success_dialog = True
                                logger.info("[ACMT LAMA SUCCESS DIALOG] %s", t)
                            elif any(w in t_lower for w in ["kadaluarsa", "ganti kata sandi", "ganti password", "ganti sandi", "akan berakhir", "sebelum", "expir"]):
                                warning_msg = t
                                logger.info("[ACMT LAMA WARNING DIALOG] %s", t)
                            else:
                                err_msg = t
                            break

                    try:
                        ok_btn = pg.locator(".x-window-dlg button:has-text('OK'), .x-window-dlg button:has-text('Ya'), button:has-text('OK')").first
                        if ok_btn.count() > 0 and ok_btn.is_visible():
                            logger.info("[ACMT LAMA] Mengklik OK pada pop-up konfirmasi...")
                            ok_btn.click()
                            pg.wait_for_timeout(500)
                    except Exception as e_ok:
                        logger.debug("[ACMT LAMA OK CLICK ERROR] %s", e_ok)

                    # Jika ada dialog sukses atau tidak ada error dialog, beri kesempatan navigasi ke Main.html selesai
                    if not err_msg or is_success_dialog:
                        for _ in range(25):
                            if "Main.htm" in pg.url or "Main.html" in pg.url or "Ipam.html" not in pg.url:
                                break
                            pg.wait_for_timeout(250)

                    if captcha_status is False and not is_success_dialog and not err_msg:
                        err_msg = "Kode CAPTCHA salah atau sudah kedaluwarsa. Periksa gambar CAPTCHA baru."
                    elif login_rpc_err and not is_success_dialog and not err_msg:
                        err_msg = login_rpc_err

                    cookies = context.cookies()
                    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if 'name' in c and 'value' in c])
                    cookie_dict = {c['name']: c['value'] for c in cookies if 'name' in c and 'value' in c}

                    is_authenticated = False
                    if not err_msg or is_success_dialog:
                        if "Main.htm" in pg.url or "Main.html" in pg.url or "Ipam.html" not in pg.url:
                            is_authenticated = True
                            err_msg = ""
                        elif is_success_dialog and "JSESSIONID" in cookie_str:
                            is_authenticated = True
                            err_msg = ""
                        elif "JSESSIONID" in cookie_str and check_acmt_lama_cookie_live(cookie_str):
                            is_authenticated = True
                            err_msg = ""

                    if "sukses" in err_msg.lower() or "berhasil" in err_msg.lower():
                        is_success_dialog = True
                        err_msg = ""
                        is_authenticated = True

                    if not is_authenticated:
                        if not err_msg:
                            err_msg = "Login tidak berhasil: periksa Username, Password, atau CAPTCHA (huruf besar/kecil)."

                        # Refresh live CAPTCHA agar form login langsung siap untuk percobaan berikutnya
                        new_captcha = ""
                        try:
                            if "Ipam.html" in pg.url and pg.locator("input[name='password']").is_visible():
                                btn_recaptcha = pg.locator("button:has-text('ReCaptcha')").first
                                if btn_recaptcha.count() > 0 and btn_recaptcha.is_visible():
                                    try:
                                        with pg.expect_response(lambda r: "CaptchaServlet" in r.url, timeout=5000):
                                            btn_recaptcha.click()
                                        pg.wait_for_timeout(300)
                                    except Exception:
                                        btn_recaptcha.click()
                                        pg.wait_for_timeout(1000)
                                img_el = pg.locator("img[src*='CaptchaServlet']").first
                                img_bytes = img_el.screenshot(timeout=5000)
                                new_captcha = f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                            else:
                                try: page.close()
                                except Exception: pass
                                page = None
                                if context:
                                    try: context.close()
                                    except Exception: pass
                                    context = None
                        except Exception:
                            try: page.close()
                            except Exception: pass
                            page = None
                            if context:
                                try: context.close()
                                except Exception: pass
                                context = None

                        result_holder["result"] = {
                            "success": False,
                            "error": err_msg,
                            "warning": warning_msg,
                            "new_captcha": new_captcha
                        }
                    else:
                        logger.info("[ACMT LAMA LOGIN WORKER] Login berhasil! Mengambil cookies.")
                        result_holder["result"] = {
                            "success": True,
                            "cookie_str": cookie_str,
                            "cookie_dict": cookie_dict,
                            "cookies": cookies,
                            "warning": warning_msg
                        }
                        try:
                            page.close()
                            context.close()
                        except Exception:
                            pass
                        page = None
                        context = None

                elif cmd == "close":
                    try:
                        if context: context.close()
                        if browser: browser.close()
                        if playwright: playwright.stop()
                    except Exception:
                        pass
                    page = None
                    context = None
                    browser = None
                    playwright = None
                    result_holder["result"] = True

            except Exception as ex:
                logger.error("[ACMT LAMA LOGIN WORKER ERROR] %s", ex)
                result_holder["error"] = ex
                try:
                    if context: context.close()
                except Exception:
                    pass
                page = None
                context = None
            finally:
                done_event.set()
                self.cmd_queue.task_done()

    def get_captcha(self, refresh=False, timeout=30):
        done = threading.Event()
        holder = {}
        self.cmd_queue.put(("get_captcha", {"refresh": refresh}, holder, done))
        if not done.wait(timeout=timeout):
            raise TimeoutError("Timeout saat memuat CAPTCHA")
        if "error" in holder:
            raise holder["error"]
        return holder.get("result")

    def submit_login(self, username, password, captcha, timeout=45):
        done = threading.Event()
        holder = {}
        self.cmd_queue.put(("submit_login", {"username": username, "password": password, "captcha": captcha}, holder, done))
        if not done.wait(timeout=timeout):
            raise TimeoutError("Timeout saat memproses login")
        if "error" in holder:
            raise holder["error"]
        return holder.get("result")

    def close(self):
        done = threading.Event()
        holder = {}
        self.cmd_queue.put(("close", {}, holder, done))
        done.wait(timeout=5)

# Singleton Instance
acmt_lama_login_mgr = AcmtLamaLoginManager()

def get_captcha_lama(refresh: bool = False) -> str:
    """Mengambil Base64 CAPTCHA ACMT Lama secara langsung."""
    return acmt_lama_login_mgr.get_captcha(refresh=refresh)

def login_direct_lama(username: str, password: str, captcha: str) -> dict:
    """Melakukan proses submit login ACMT Lama via headless browser dan menyimpan sesi ke cache."""
    res = acmt_lama_login_mgr.submit_login(username.strip(), password.strip(), captcha.strip())
    err_text = str(res.get("error", "") or res.get("message", "")).strip()

    # Safety override jika PLN mengembalikan dialog konfirmasi SUKSES
    if ("sukses" in err_text.lower() or "berhasil" in err_text.lower()) and not res.get("success"):
        res["success"] = True
        logger.info("[ACMT LAMA] Override login sukses dari pesan dialog: %s", err_text)

    if not res.get("success"):
        new_captcha = res.get("new_captcha", "")
        if not new_captcha:
            try:
                new_captcha = acmt_lama_login_mgr.get_captcha(refresh=True)
            except Exception:
                pass
        return {
            "success": False,
            "message": res.get("error", "Login gagal: periksa Username, Password, atau CAPTCHA"),
            "new_captcha": new_captcha
        }

    cookie_str = res.get("cookie_str", "")
    warn = res.get("warning", "")
    u_clean = username.strip()
    if cookie_str:
        set_cookie_string(cookie_str, set_by=u_clean)
        if not _session_new_cache.get("token"):
            set_priority("lama_first")
    msg = f"Login ACMT Lama Berhasil! Terhubung sebagai {u_clean}."
    if warn:
        msg += f" (Catatan: {warn})"
    logger.info("[ACMT LAMA LOGIN BERHASIL] %s", msg)
    return {"success": True, "message": msg, "cookies": cookie_str}

def reset_all_sessions() -> dict:
    """Menghapus seluruh sesi ACMT New & ACMT Lama baik dari memory maupun file disk."""
    _session_cache["cookie_string"] = None
    _session_cache["set_by"] = None
    _session_cache["set_at"] = None

    _session_new_cache["token"] = None
    _session_new_cache["username"] = None
    _session_new_cache["unitup"] = None
    _session_new_cache["set_by"] = None
    _session_new_cache["set_at"] = None

    for p in [SESSION_NEW_FILE, SESSION_LAMA_FILE]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception as e:
                logger.warning("Gagal menghapus %s: %s", p, e)
    return {"success": True, "message": "Semua sesi ACMT berhasil di-reset!"}
