"""
Router: /api/foto — Proxy foto meter ACMT PLN (Dual Mode: ACMT Lama & ACMT New)
"""

import os
import logging
import urllib.parse
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.pln_proxy import (
    get_captcha_lama,
    login_direct_lama,
    reset_all_sessions,
    check_acmt_lama_cookie_live,
    fetch_photo, 
    fetch_photo_new, 
    fetch_photo_smart,
    set_cookie_string, 
    set_token_new,
    set_priority,
    login_acmt_new,
    get_session_status,
    parse_cookie_input,
    _session_cache, 
    _session_new_cache,
    URL_ACMT_NEW_API,
    PHOTO_URL, 
    _BASE_HEADERS
)
from app.routers.auth import get_current_user
from app.models import User, RoleEnum

logger = logging.getLogger(__name__)
router = APIRouter()

SYNC_SECRET = os.getenv("BOOKMARKLET_SECRET", "metrik-sync-2026")


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class DirectLoginNewRequest(BaseModel):
    username: str
    password: str
    enkripsi: Optional[str] = ""

class DirectLoginLamaRequest(BaseModel):
    username: str
    password: str
    captcha: str

class SaveCookiesLamaRequest(BaseModel):
    cookies: str

class SessionPayload(BaseModel):
    cookie_string: str   # full cookie ACMT Lama: "JSESSIONID=x; TS01be508d=x; ..."
    set_by: str = "admin"

class SessionNewPayload(BaseModel):
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enkripsi: Optional[str] = None
    unitup: Optional[str] = None
    set_by: str = "admin"

class PriorityPayload(BaseModel):
    priority: str        # "new_first" | "lama_first"

class ExtensionSyncPayload(BaseModel):
    cookie_string: Optional[str] = None
    token_new: Optional[str] = None
    username: Optional[str] = None
    unitup: Optional[str] = None
    secret_key: str


# ─── Session Endpoints ────────────────────────────────────────────────────────

@router.get("/foto/session/status")
def session_status(current_user: User = Depends(get_current_user)):
    """Cek status sesi ACMT Lama dan ACMT New serta prioritas pencarian."""
    return get_session_status()


@router.post("/foto/priority")
def update_photo_priority(payload: PriorityPayload, current_user: User = Depends(get_current_user)):
    """Mengatur prioritas server foto (new_first atau lama_first)."""
    p = set_priority(payload.priority)
    return {"ok": True, "priority": p, "message": f"Prioritas pencarian foto diatur ke: {p}"}


@router.post("/foto/session")
def update_session(payload: SessionPayload, current_user: User = Depends(get_current_user)):
    """
    Simpan sesi ACMT Lama dari browser.
    Mendukung format string biasa (JSESSIONID=xxx; ...), format JSON array, format JSON object, dsb.
    """
    cleaned = parse_cookie_input(payload.cookie_string)
    if not cleaned or len(cleaned) < 10:
        raise HTTPException(status_code=400, detail="Cookie / Sesi tidak valid")
    if "JSESSIONID" not in cleaned:
        raise HTTPException(status_code=400, detail="Cookie / Sesi harus mengandung JSESSIONID")
    set_cookie_string(cleaned, set_by=payload.set_by)
    status = get_session_status()
    return {
        "ok": True, 
        "message": "Sesi ACMT Lama berhasil disimpan & dicache permanen!", 
        "cookie_keys": status["cookie_keys"]
    }


@router.post("/foto/session-new")
async def update_session_new(payload: SessionNewPayload, current_user: User = Depends(get_current_user)):
    """
    Simpan token ACMT New atau login langsung menggunakan Username & Password.
    """
    # 1. Jika pengguna memberikan username & password -> Login langsung ke ACMT New API
    if payload.username and payload.password:
        res = await login_acmt_new(
            username=payload.username, 
            password=payload.password, 
            enkripsi=payload.enkripsi or "", 
            unitup=payload.unitup or ""
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("message", "Login ACMT New gagal"))
        return res

    # 2. Jika pengguna memasukkan Bearer Token langsung
    if payload.token and len(payload.token.strip()) > 10:
        set_token_new(
            token=payload.token, 
            username=payload.username, 
            unitup=payload.unitup, 
            set_by=payload.set_by
        )
        status = get_session_status()
        return {
            "ok": True, 
            "message": "Token ACMT New berhasil disimpan", 
            "status": status.get("acmt_new")
        }

    raise HTTPException(status_code=400, detail="Harap masukkan Token Bearer atau Username & Password ACMT New")


@router.post("/foto/sync-extension")
def sync_cookie_from_extension(payload: ExtensionSyncPayload):
    """Endpoint aman untuk Ekstensi Chrome & Bookmarklet tanpa JWT Token."""
    if payload.secret_key != SYNC_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    updated_items = []
    
    # Sinkronisasi ACMT Lama (jika ada cookie_string)
    if payload.cookie_string and len(payload.cookie_string) >= 10:
        cleaned_cookie = parse_cookie_input(payload.cookie_string)
        if "JSESSIONID" in cleaned_cookie:
            set_cookie_string(cleaned_cookie, set_by="chrome-extension")
            updated_items.append("ACMT Lama (Cookie)")

    # Sinkronisasi ACMT New (jika ada token_new)
    if payload.token_new and len(payload.token_new) >= 10:
        set_token_new(
            token=payload.token_new,
            username=payload.username,
            unitup=payload.unitup,
            set_by="chrome-extension"
        )
        updated_items.append("ACMT New (Token)")

    if not updated_items:
        raise HTTPException(status_code=400, detail="Data sync tidak valid (tidak ada cookie maupun token)")

    status = get_session_status()
    return {
        "ok": True, 
        "message": f"Berhasil disinkronkan & disimpan ke cache: {', '.join(updated_items)}", 
        "cookie_keys": status.get("cookie_keys"),
        "acmt_new": status.get("acmt_new")
    }


# ─── Foto Retrieval Endpoint ──────────────────────────────────────────────────

@router.get("/foto")
async def get_foto_meter(
    request: Request,
    idpel:    str = Query(...),
    blth:     str = Query(...),
    fotoke:   str = Query(...),
    source:   str = Query("auto"),                # auto | lama | new
    priority: Optional[str] = Query(None),        # new_first | lama_first
    unitup:   Optional[str] = Query(None),
):
    """
    Proxy foto meter dari ACMT PLN (Mendukung ACMT Lama & ACMT New).
    - source="auto": Menggunakan smart fallback sesuai prioritas ('new_first' atau 'lama_first')
    - source="lama": Khusus ambil dari ACMT Lama
    - source="new": Khusus ambil dari ACMT New
    """
    client_cookie_raw = request.cookies.get("metrik_acmt_session")
    client_cookie = urllib.parse.unquote(client_cookie_raw) if client_cookie_raw else None

    client_token_raw = request.cookies.get("metrik_acmt_new_token") or request.headers.get("X-ACMT-New-Token")
    client_token = urllib.parse.unquote(client_token_raw) if client_token_raw else None

    try:
        image_bytes, content_type, source_used = await fetch_photo_smart(
            idpel=idpel, 
            blth=blth, 
            fotoke=fotoke, 
            client_cookie=client_cookie,
            client_token=client_token,
            source=source,
            priority=priority,
            unitup=unitup
        )
        return Response(
            content=image_bytes,
            media_type=content_type or "image/jpeg",
            headers={
                "Cache-Control": "private, max-age=3600",
                "X-Photo-Source": source_used,
                "Access-Control-Expose-Headers": "X-Photo-Source"
            },
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "SESSION_EXPIRED" in msg or "belum diset" in msg:
            raise HTTPException(status_code=401, detail=msg)
        if "tidak tersedia" in msg or "tidak ditemukan" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=502, detail=msg)
    except Exception as exc:
        logger.exception("Error tidak terduga saat ambil foto meter")
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Debug Endpoints ──────────────────────────────────────────────────────────

@router.get("/foto/debug")
async def debug_acmt_response(
    idpel:  str = Query(...),
    blth:   str = Query(...),
    fotoke: str = Query("1"),
    current_user: User = Depends(get_current_user)
):
    """Debug: lihat raw response dari ACMT Lama tanpa filter."""
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Hanya admin yang dapat mengakses debug")
    cookie_string = _session_cache.get("cookie_string", "")
    params  = {"idpel": idpel, "nomor_meter": "null", "fotoke": fotoke, "blth": blth, "isPhoto": "null"}
    headers = {**_BASE_HEADERS, "Cookie": cookie_string}

    async with httpx.AsyncClient(timeout=20.0, verify=False, follow_redirects=False) as client:
        resp = await client.get(PHOTO_URL, params=params, headers=headers)

    ct = resp.headers.get("content-type", "")
    return {
        "status_code":    resp.status_code,
        "content_type":   ct,
        "content_length": len(resp.content),
        "resp_headers":   dict(resp.headers),
        "body_preview":   resp.text[:500] if "text" in ct else f"<binary {len(resp.content)} bytes>",
        "magic_bytes_hex": resp.content[:8].hex() if resp.content else "",
        "cookie_keys_sent": [p.split("=")[0].strip() for p in cookie_string.split(";") if "=" in p],
    }


@router.get("/foto/debug-proxy")
async def debug_proxy(current_user: User = Depends(get_current_user)):
    """Debug: test status proxy connection ACMT Lama & New."""
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Hanya admin yang dapat mengakses debug")
    
    cookie_string = _session_cache.get("cookie_string", "")
    token_new = _session_new_cache.get("token", "")
    
    dapat_reach_lama = False
    test_status_lama = None
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.head("https://portalapp.iconpln.co.id/acmt/Main.htm", headers=_BASE_HEADERS)
            dapat_reach_lama = True
            test_status_lama = resp.status_code
    except Exception as e:
        logger.error(f"Cannot reach ACMT Lama: {e}")

    dapat_reach_new = False
    test_status_new = None
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(f"{URL_ACMT_NEW_API}/health", headers={"Accept": "application/json"})
            dapat_reach_new = True
            test_status_new = resp.status_code
    except Exception as e:
        logger.error(f"Cannot reach ACMT New: {e}")
        
    return {
        "acmt_lama": {
            "cookie_set": bool(cookie_string),
            "reach_ok": dapat_reach_lama,
            "status_code": test_status_lama
        },
        "acmt_new": {
            "token_set": bool(token_new),
            "username": _session_new_cache.get("username"),
            "priority": _session_new_cache.get("priority", "new_first"),
            "reach_ok": dapat_reach_new,
            "status_code": test_status_new
        }
    }


# ─── Direct Login & Live CAPTCHA Routes (Identik dengan AP2T New) ──────────────

@router.post("/foto/login_direct_new")
@router.post("/session/login_direct_new")
async def handle_login_direct_new(payload: DirectLoginNewRequest):
    """Login langsung ke ACMT New API menggunakan Username, Password, Enkripsi."""
    if not payload.username or not payload.password:
        return {"success": False, "message": "Username dan Password ACMT New wajib diisi"}
    res = await login_acmt_new(
        username=payload.username,
        password=payload.password,
        enkripsi=payload.enkripsi or "",
        unitup=""
    )
    if res.get("ok"):
        return {"success": True, "message": res.get("message", "Login ACMT New Berhasil!"), "data": res}
    return {"success": False, "message": res.get("message", "Login ACMT New Gagal")}


@router.get("/foto/acmt_lama/captcha")
@router.get("/session/acmt_lama/captcha")
def handle_get_captcha_lama(refresh: bool = False):
    """Mengambil live CAPTCHA dari ACMT Lama via headless browser."""
    try:
        b64 = get_captcha_lama(refresh=refresh)
        return {"success": True, "captcha_b64": b64}
    except Exception as e:
        logger.error("[CAPTCHA ERROR] %s", e)
        return {"success": False, "message": f"Gagal memuat CAPTCHA dari server PLN: {str(e)}"}


@router.post("/foto/login_direct_lama")
@router.post("/session/login_direct_lama")
def handle_login_direct_lama(payload: DirectLoginLamaRequest):
    """Submit login langsung ke ACMT Lama dengan verifikasi CAPTCHA & simpan cookie permanen."""
    if not payload.username or not payload.password or not payload.captcha:
        return {"success": False, "message": "Username, Password, dan kode CAPTCHA wajib diisi"}
    try:
        res = login_direct_lama(
            username=payload.username,
            password=payload.password,
            captcha=payload.captcha
        )
        return res
    except Exception as e:
        logger.error("[LOGIN DIRECT LAMA ERROR] %s", e)
        return {"success": False, "message": f"Gagal memproses login: {str(e)}"}


@router.post("/foto/save_cookies_lama")
@router.post("/session/save_cookies_lama")
def handle_save_cookies_lama(payload: SaveCookiesLamaRequest):
    """Simpan cookie ACMT Lama manual."""
    cleaned = parse_cookie_input(payload.cookies)
    if not cleaned or len(cleaned) < 10:
        return {"success": False, "message": "Cookie tidak valid"}
    if "JSESSIONID" not in cleaned:
        return {"success": False, "message": "Cookie harus menyertakan JSESSIONID"}
    
    is_live = check_acmt_lama_cookie_live(cleaned)
    set_cookie_string(cleaned, set_by="manual-input")
    if not is_live:
        return {
            "success": True, 
            "message": "Cookie ACMT Lama disimpan (Perhatian: Server ACMT merespon redirect ke Ipam.html. Pastikan Anda sudah login di browser portal ACMT)."
        }
    return {"success": True, "message": "Cookie ACMT Lama valid & berhasil terhubung!"}


@router.post("/foto/session/reset")
@router.post("/session/reset")
@router.post("/session/logout")
def handle_reset_session():
    """Reset dan hapus seluruh sesi ACMT New & ACMT Lama."""
    return reset_all_sessions()
