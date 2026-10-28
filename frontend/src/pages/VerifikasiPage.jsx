import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/axios'
import { toast } from 'sonner'
import { useAuthStore } from '../store/authStore'
import {
    Camera, CheckCircle2, Clock, AlertTriangle, XCircle, FileCheck, Edit3,
    Search, ChevronLeft, ChevronRight, RefreshCw, Shield, ShieldCheck, Key,
    Bot, User, TrendingUp, TrendingDown, Layers, HelpCircle, RotateCcw, X,
    Info, Tag, Building2, Hash, FileText, Sparkles, ArrowUpDown, Check, Copy,
    CheckSquare2, Zap, SlidersHorizontal, Lock, Eye, EyeOff, Server, Trash2,
    AlertCircle, Plus, ClipboardPaste
} from 'lucide-react'

// ─── Foto Meter Helpers ───────────────────────────────────────────────────────
const FOTO_MONTHS = 6   // jumlah bulan ke belakang yang ditampilkan
const FOTO_PER_MONTH = 3

function getBlthList() {
    const list = []
    const now = new Date()
    for (let i = 0; i < FOTO_MONTHS; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, '0')
        list.push(`${y}${m}`)
    }
    return list
}

function ZoomableImage({ src, style, onClick, allowZoom = true }) {
    const [magnifierActive, setMagnifierActive] = useState(false);
    const [{ x, y, imgX, imgY, imgWidth, imgHeight }, setMagnifierState] = useState({ x: 0, y: 0, imgX: 0, imgY: 0, imgWidth: 0, imgHeight: 0 });
    const divRef = useRef(null);
    const imgRef = useRef(null);
    
    // Konfigurasi Kaca Pembesar
    const MAGNIFIER_SIZE = 250; 
    const ZOOM_LEVEL = 2.5;

    const handleMouseMove = (e) => {
        if (!allowZoom || !magnifierActive || !divRef.current || !imgRef.current) return;
        
        const divRect = divRef.current.getBoundingClientRect();
        const img = imgRef.current;
        const imgRect = img.getBoundingClientRect();
        
        if (!img.naturalWidth || !img.naturalHeight) return;

        const naturalRatio = img.naturalWidth / img.naturalHeight;
        const elementRatio = imgRect.width / imgRect.height;
        
        let renderedWidth = imgRect.width;
        let renderedHeight = imgRect.height;
        
        if (naturalRatio > elementRatio) {
            renderedHeight = imgRect.width / naturalRatio;
        } else {
            renderedWidth = imgRect.height * naturalRatio;
        }
        
        const imgRectLeft = imgRect.left + (imgRect.width - renderedWidth) / 2;
        const imgRectTop = imgRect.top + (imgRect.height - renderedHeight) / 2;

        const clientX = e.clientX;
        const clientY = e.clientY;
        if (clientX === undefined) return;

        const currentImgX = clientX - imgRectLeft;
        const currentImgY = clientY - imgRectTop;

        if (currentImgX < -5 || currentImgX > renderedWidth + 5 || currentImgY < -5 || currentImgY > renderedHeight + 5) {
            return;
        }

        const x = clientX - divRect.left - (MAGNIFIER_SIZE / 2);
        const y = clientY - divRect.top - (MAGNIFIER_SIZE / 2);

        setMagnifierState({
            x, y,
            imgX: currentImgX,
            imgY: currentImgY,
            imgWidth: renderedWidth,
            imgHeight: renderedHeight
        });
    };

    const handleClick = (e) => {
        if (allowZoom) {
            e.stopPropagation();
            const syntheticEvent = { clientX: e.clientX, clientY: e.clientY };
            if (!magnifierActive) {
                setMagnifierActive(true);
                setTimeout(() => handleMouseMove(syntheticEvent), 0);
            } else {
                setMagnifierActive(false);
            }
        }
        if (onClick) onClick(e);
    };

    return (
        <div 
            ref={divRef}
            style={{ ...style, position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setMagnifierActive(false)}
        >
            <img 
                ref={imgRef}
                src={src} 
                alt="Meter" 
                onClick={handleClick}
                style={{ 
                    display: 'block',
                    maxWidth: '100%', 
                    maxHeight: '100%', 
                    objectFit: 'contain',
                    cursor: allowZoom ? (magnifierActive ? 'none' : 'zoom-in') : 'pointer'
                }} 
            />
            {allowZoom && magnifierActive && (
                <div
                    onClick={handleClick} 
                    style={{
                        position: "absolute",
                        cursor: 'none',
                        width: `${MAGNIFIER_SIZE}px`,
                        height: `${MAGNIFIER_SIZE}px`,
                        left: `${x}px`,
                        top: `${y}px`,
                        border: "2px solid #eab308", 
                        backgroundColor: "#fff",
                        backgroundImage: `url('${src}')`,
                        backgroundRepeat: "no-repeat",
                        backgroundSize: `${imgWidth * ZOOM_LEVEL}px ${imgHeight * ZOOM_LEVEL}px`,
                        backgroundPositionX: `${-imgX * ZOOM_LEVEL + MAGNIFIER_SIZE / 2}px`,
                        backgroundPositionY: `${-imgY * ZOOM_LEVEL + MAGNIFIER_SIZE / 2}px`,
                        boxShadow: "0 10px 25px rgba(0,0,0,0.6)",
                        zIndex: 9999,
                        borderRadius: 8
                    }}
                />
            )}
        </div>
    );
}

function FotoModal({ foto, onClose }) {
    return (
        <div
            onClick={onClose}
            style={{
                position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', zIndex: 200,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12
            }}
        >
            <div onClick={e => e.stopPropagation()} className="photo-modal-view"
                style={{
                    background: '#1e293b', borderRadius: 10, padding: 16, maxWidth: '90vw', maxHeight: '90vh',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ color: '#94a3b8', fontSize: 12 }}>
                            PHOTO {foto.fotoke} &mdash; {foto.blth.slice(0, 4)}/{foto.blth.slice(4)} &nbsp;|&nbsp; {foto.idpel}
                        </span>
                        {foto.source && (
                            <span style={{
                                padding: '2px 7px', borderRadius: 4, fontSize: 10, fontWeight: 600,
                                background: foto.source.includes('New') ? '#4f46e5' : '#0284c7',
                                color: '#ffffff'
                            }}>
                                {foto.source}
                            </span>
                        )}
                    </div>
                    <button onClick={onClose}
                        style={{
                            background: '#334155', border: 'none', color: '#94a3b8', borderRadius: 5,
                            width: 26, height: 26, cursor: 'pointer', fontSize: 15, lineHeight: 1
                        }}>✕</button>
                </div>
                {foto.loading && <div style={{ color: '#94a3b8', padding: 40, fontSize: 13 }}>Memuat foto...</div>}
                {foto.error && <div style={{ color: '#f87171', padding: 20, fontSize: 12, textAlign: 'center' }}>{foto.error}</div>}
                {foto.url && <ZoomableImage src={foto.url} style={{ maxWidth: '80vw', maxHeight: '75vh', borderRadius: 6 }} allowZoom={true} />}
            </div>
        </div>
    )
}

function LatestPhoto({ idpel, blth }) {
    const [fotoState, setFotoState] = useState({ loading: true, url: null, error: null, source: null })
    const [showFull, setShowFull] = useState(false)

    useEffect(() => {
        let isMounted = true
        setFotoState({ loading: true, url: null, error: null, source: null })
        const token = useAuthStore.getState().token
        fetch(`/api/foto?idpel=${encodeURIComponent(idpel)}&blth=${blth}&fotoke=1`, { headers: { Authorization: `Bearer ${token}` } })
            .then(async r => {
                if (!r.ok) {
                    const err = await r.json().catch(() => ({}))
                    throw new Error(err.detail || `HTTP ${r.status}`)
                }
                const photoSource = r.headers.get('X-Photo-Source') || 'ACMT'
                const blob = await r.blob()
                if (isMounted) setFotoState({ loading: false, url: URL.createObjectURL(blob), error: null, source: photoSource })
            })
            .catch(e => {
                const msg = e.message.includes('401') || e.message.includes('EXPIRED') || e.message.includes('belum diset')
                    ? 'Sesi ACMT harus di-input ulang'
                    : e.message;
                if (isMounted) setFotoState({ loading: false, url: null, error: msg, source: null })
            })
        return () => { isMounted = false }
    }, [idpel, blth])

    return (
        <>
            <div
                onClick={() => fotoState.url && setShowFull(true)}
                style={{ width: '100%', height: 400, background: '#0f172a', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e2e8f0', overflow: 'hidden', marginBottom: 16, cursor: fotoState.url ? 'pointer' : 'default', position: 'relative' }}
                title={fotoState.url ? "Klik untuk melihat layar penuh" : ""}
            >
                {fotoState.loading && <div style={{ fontSize: 11, color: '#94a3b8' }}>Memuat foto terbaru...</div>}
                {fotoState.error && <div style={{ fontSize: 11, color: '#ef4444', textAlign: 'center', padding: 10 }}>{fotoState.error}</div>}
                {fotoState.url && (
                    <>
                        <ZoomableImage src={fotoState.url} style={{ width: '100%', height: '100%' }} allowZoom={false} />
                        {fotoState.source && (
                            <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(0,0,0,0.65)', color: '#38bdf8', padding: '3px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ width: 6, height: 6, borderRadius: '50%', background: fotoState.source.includes('New') ? '#818cf8' : '#38bdf8' }}></span>
                                {fotoState.source}
                            </div>
                        )}
                        <div style={{ position: 'absolute', bottom: 8, right: 8, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '4px 8px', borderRadius: 4, fontSize: 10, pointerEvents: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Search size={11} /> Klik untuk Layar Penuh
                        </div>
                    </>
                )}
            </div>
            {showFull && (
                <FotoModal
                    foto={{ idpel, blth, fotoke: 1, url: fotoState.url, loading: false, error: null, source: fotoState.source }}
                    onClose={() => setShowFull(false)}
                />
            )}
        </>
    )
}

const STATUS_LABEL = {
    PENDING: 'Pending',
    VERIFIED_OK: 'Selesai',
    VERIFIED_REJECT: 'Tolak',
    NEED_INVESTIGATION: 'Investigasi'
}
const STATUS_STYLE = {
    PENDING: { bg: '#f1f5f9', color: '#64748b', border: '#e2e8f0' },
    VERIFIED_OK: { bg: '#f0fdf4', color: '#16a34a', border: '#bbf7d0' },
    VERIFIED_REJECT: { bg: '#fef2f2', color: '#dc2626', border: '#fecaca' },
    NEED_INVESTIGATION: { bg: '#fffbeb', color: '#d97706', border: '#fde68a' },
}

// Alasan perbedaan sekarang diambil dinamis dari API

function Badge({ status }) {
    const s = STATUS_STYLE[status] || STATUS_STYLE.PENDING
    return (
        <span style={{ padding: '3px 9px', borderRadius: 4, fontSize: 11, fontWeight: 500, background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
            {STATUS_LABEL[status] || status}
        </span>
    )
}

const inputStyle = { height: 34, padding: '0 11px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, outline: 'none', background: '#fff', color: '#1e293b' }
const btnBase = { border: 'none', borderRadius: 6, padding: '9px 0', cursor: 'pointer', fontWeight: 600, fontSize: 12, width: '100%' }

// ─── ACMT Session Panel & Login Modal (Identik dengan AP2T New) ───────────────
function AcmtSessionPanel() {
    const [showModal, setShowModal] = useState(false);
    const [showGuide, setShowGuide] = useState(false);
    const [portalTab, setPortalTab] = useState('new'); // 'new' | 'lama'
    const [loading, setLoading] = useState(false);

    // State ACMT New
    const [userNew, setUserNew] = useState('');
    const [passNew, setPassNew] = useState('');
    const [enkripsiNew, setEnkripsiNew] = useState('');
    const [showPassNew, setShowPassNew] = useState(false);
    const [showEnkripsiNew, setShowEnkripsiNew] = useState(false);
    const [errorNew, setErrorNew] = useState('');

    // State ACMT Lama
    const [userLama, setUserLama] = useState('');
    const [passLama, setPassLama] = useState('');
    const [captchaLama, setCaptchaLama] = useState('');
    const [showPassLama, setShowPassLama] = useState(false);
    const [captchaB64, setCaptchaB64] = useState('');
    const [loadingCaptcha, setLoadingCaptcha] = useState(false);
    const [errorLama, setErrorLama] = useState('');
    const [showManualLama, setShowManualLama] = useState(false);
    const [manualCookieLama, setManualCookieLama] = useState('');

    const { data: status = null, refetch: loadStatus } = useQuery({
        queryKey: ['acmt-session-status'],
        queryFn: async () => {
            const r = await api.get('/api/foto/session/status');
            return r.data;
        },
        refetchInterval: 30000
    });

    const hasLocalCookie = typeof document !== 'undefined' && document.cookie.includes('metrik_acmt_session');
    const hasLama = Boolean(status?.acmt_lama?.has_session || hasLocalCookie);
    const hasNew = Boolean(status?.acmt_new?.has_session);
    const hasAnySession = hasLama || hasNew;

    // Muat live CAPTCHA ACMT Lama
    const fetchCaptcha = async (refresh = false) => {
        setLoadingCaptcha(true);
        setErrorLama('');
        try {
            const res = await api.get(`/api/foto/acmt_lama/captcha?refresh=${refresh}`);
            if (res.data?.success && res.data?.captcha_b64) {
                setCaptchaB64(res.data.captcha_b64);
            } else {
                setErrorLama(res.data?.message || 'Gagal memuat CAPTCHA');
            }
        } catch (e) {
            setErrorLama('Gagal memuat CAPTCHA dari server PLN');
        } finally {
            setLoadingCaptcha(false);
        }
    };

    // Buka modal dan muat CAPTCHA jika membuka tab Lama
    const openModal = (tab = 'new') => {
        setPortalTab(tab);
        setShowModal(true);
        setErrorNew('');
        setErrorLama('');
        if (tab === 'lama') {
            fetchCaptcha(true);
        }
    };

    const handleTabSwitch = (tab) => {
        setPortalTab(tab);
        setErrorNew('');
        setErrorLama('');
        if (tab === 'lama') {
            fetchCaptcha(true);
        }
    };

    // Submit Login Langsung ACMT New
    const handleLoginNew = async (e) => {
        if (e) e.preventDefault();
        setErrorNew('');
        if (!userNew.trim() || !passNew.trim()) {
            setErrorNew('Username dan Password ACMT New wajib diisi');
            return;
        }

        setLoading(true);
        try {
            const res = await api.post('/api/foto/login_direct_new', {
                username: userNew.trim(),
                password: passNew.trim(),
                enkripsi: enkripsiNew.trim()
            });

            if (res.data?.success) {
                toast.success(res.data.message || 'Login ACMT New Berhasil!');
                setPassNew('');
                setEnkripsiNew('');
                setShowModal(false);
                await loadStatus();
            } else {
                setErrorNew(res.data?.message || 'Login gagal: periksa Username/Password/Enkripsi');
            }
        } catch (err) {
            setErrorNew('Gagal menghubungi server: ' + (err.response?.data?.message || err.message));
        } finally {
            setLoading(false);
        }
    };

    // Submit Login Langsung ACMT Lama
    const handleLoginLama = async (e) => {
        if (e) e.preventDefault();
        setErrorLama('');
        if (!userLama.trim() || !passLama.trim() || !captchaLama.trim()) {
            setErrorLama('Username, Password, dan kode CAPTCHA wajib diisi');
            return;
        }

        setLoading(true);
        try {
            const res = await api.post('/api/foto/login_direct_lama', {
                username: userLama.trim(),
                password: passLama.trim(),
                captcha: captchaLama.trim()
            }, { timeout: 45000 });

            const isSuccess = Boolean(res.data?.success || (res.data?.message && res.data.message.toUpperCase().includes('SUKSES')));
            if (isSuccess) {
                toast.success(res.data?.message || 'Login ACMT Lama Berhasil!');
                setPassLama('');
                setCaptchaLama('');
                setShowModal(false);
                await loadStatus();
            } else {
                setErrorLama(res.data?.message || 'Login gagal: periksa Username, Password, atau CAPTCHA');
                if (res.data?.new_captcha) {
                    setCaptchaB64(res.data.new_captcha);
                } else {
                    fetchCaptcha(true);
                }
                setCaptchaLama('');
            }
        } catch (err) {
            setErrorLama('Gagal menghubungi server: ' + (err.response?.data?.message || err.message));
        } finally {
            setLoading(false);
        }
    };

    // Submit Manual Cookie ACMT Lama (Opsional / Fallback)
    const handleSaveManualCookieLama = async () => {
        if (!manualCookieLama.trim()) {
            toast.error('Masukkan Cookie JSESSIONID');
            return;
        }
        setLoading(true);
        try {
            const res = await api.post('/api/foto/save_cookies_lama', {
                cookies: manualCookieLama.trim()
            });
            if (res.data?.success) {
                toast.success(res.data.message || 'Cookie ACMT Lama berhasil disimpan!');
                setManualCookieLama('');
                setShowManualLama(false);
                setShowModal(false);
                await loadStatus();
            } else {
                toast.error(res.data?.message || 'Gagal menyimpan cookie');
            }
        } catch (err) {
            toast.error('Gagal menghubungi server: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    // Reset Semua Sesi
    const handleResetAll = async () => {
        if (!window.confirm('Keluar dan reset semua sesi ACMT (New & Lama)?')) return;
        setLoading(true);
        try {
            await api.post('/api/foto/session/reset');
            toast.success('Semua sesi ACMT berhasil di-reset!');
            setUserNew('');
            setPassNew('');
            setEnkripsiNew('');
            setUserLama('');
            setPassLama('');
            setCaptchaLama('');
            setCaptchaB64('');
            setShowModal(false);
            await loadStatus();
        } catch (err) {
            toast.error('Gagal reset sesi: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Top Bar Widget */}
            <div style={{
                background: hasAnySession ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${hasAnySession ? '#bbf7d0' : '#fecaca'}`,
                borderRadius: 8, padding: '10px 14px', marginBottom: 16,
                display: 'flex', gap: 12, flexDirection: 'column'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{
                        fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                        color: hasAnySession ? '#15803d' : '#dc2626', letterSpacing: '0.5px',
                        display: 'flex', alignItems: 'center', gap: 5
                    }}>
                        {hasAnySession ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        {hasAnySession ? 'Sesi ACMT Siap' : 'Sesi ACMT Belum Diset'}
                    </span>

                    {/* Badge ACMT New */}
                    <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                        background: hasNew ? '#e0e7ff' : '#f1f5f9',
                        color: hasNew ? '#3730a3' : '#64748b',
                        border: `1px solid ${hasNew ? '#c7d2fe' : '#e2e8f0'}`,
                        display: 'flex', alignItems: 'center', gap: 4
                    }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: hasNew ? '#4f46e5' : '#94a3b8' }}></span>
                        ACMT New: {hasNew ? (status?.acmt_new?.username || 'Aktif') : 'Off'}
                    </span>

                    {/* Badge ACMT Lama */}
                    <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                        background: hasLama ? '#dcfce7' : '#f1f5f9',
                        color: hasLama ? '#166534' : '#64748b',
                        border: `1px solid ${hasLama ? '#bbf7d0' : '#e2e8f0'}`,
                        display: 'flex', alignItems: 'center', gap: 4
                    }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: hasLama ? '#16a34a' : '#94a3b8' }}></span>
                        ACMT Lama: {hasLama ? (hasLocalCookie ? 'Lokal (Ekstensi)' : 'Aktif') : 'Off'}
                    </span>

                    {/* Selector Prioritas Server */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 4 }}>
                        <span style={{ fontSize: 10, color: '#64748b', fontWeight: 600 }}>Prioritas:</span>
                        <select
                            value={status?.priority || 'new_first'}
                            onChange={async (e) => {
                                const p = e.target.value;
                                try {
                                    await api.post('/api/foto/priority', { priority: p });
                                    toast.success(`Prioritas diatur ke: ${p === 'new_first' ? 'ACMT New' : 'ACMT Lama'}`);
                                    loadStatus();
                                } catch (err) {
                                    toast.error('Gagal mengubah prioritas');
                                }
                            }}
                            style={{
                                fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
                                border: '1px solid #cbd5e1', background: '#ffffff', color: '#1e293b',
                                cursor: 'pointer', outline: 'none'
                            }}
                        >
                            <option value="new_first">ACMT New</option>
                            <option value="lama_first">ACMT Lama</option>
                        </select>
                    </div>

                    <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                        <button onClick={() => setShowGuide(g => !g)}
                            style={{
                                fontSize: 11, padding: '4px 10px', border: '1px solid #cbd5e1',
                                borderRadius: 6, background: '#fff', cursor: 'pointer', color: '#334155',
                                display: 'flex', alignItems: 'center', gap: 5, fontWeight: 500
                            }}>
                            <HelpCircle size={12} color="#64748b" /> Panduan
                        </button>
                        <button onClick={() => openModal(hasNew ? 'new' : (hasLama ? 'lama' : 'new'))}
                            style={{
                                fontSize: 11, padding: '4px 12px', border: 'none', borderRadius: 6,
                                background: hasAnySession ? '#16a34a' : '#dc2626',
                                color: '#fff', cursor: 'pointer', fontWeight: 600,
                                display: 'flex', alignItems: 'center', gap: 5,
                                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                            }}>
                            {hasAnySession ? (
                                <><SlidersHorizontal size={12} /> Kelola Sesi ACMT</>
                            ) : (
                                <><Plus size={12} /> Hubungkan Sesi ACMT</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Panduan */}
                {showGuide && (
                    <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: 12, fontSize: 11, color: '#374151', lineHeight: 1.7 }}>
                        <strong>Panduan Koneksi Foto Meter (Dual Mode):</strong>
                        <ul style={{ margin: '6px 0 0 16px', padding: 0 }}>
                            <li><strong>ACMT New:</strong> Masukkan Username, Password, dan Enkripsi di modal login. Sesi token langsung tersimpan otomatis di cache server.</li>
                            <li><strong>ACMT Lama:</strong> Masukkan Username, Password, dan kode verifikasi CAPTCHA live yang muncul di modal. Cookies langsung tersimpan & dicache otomatis.</li>
                            <li><strong>Otomatis Tanpa Copy-Paste:</strong> Anda tidak perlu lagi menyalin string JSON atau token bearer manual.</li>
                        </ul>
                    </div>
                )}
            </div>

            {/* MODAL LOGIN PORTAL ACMT */}
            {showModal && (
                <div style={{
                    position: 'fixed', inset: 0,
                    backgroundColor: 'rgba(15, 23, 42, 0.65)',
                    backdropFilter: 'blur(3px)',
                    zIndex: 9999,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    padding: 16
                }} onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}>
                    <div style={{
                        background: '#ffffff',
                        borderRadius: 12,
                        width: '100%', maxWidth: 480,
                        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1)',
                        overflow: 'hidden',
                        border: '1px solid #e2e8f0',
                        display: 'flex', flexDirection: 'column'
                    }}>
                        {/* Modal Header */}
                        <div style={{
                            padding: '16px 20px',
                            borderBottom: '1px solid #e2e8f0',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div style={{
                                    width: 36, height: 36, borderRadius: 8,
                                    background: '#eff6ff', border: '1px solid #dbeafe',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    color: '#2563eb'
                                }}>
                                    <Key size={18} />
                                </div>
                                <div>
                                    <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: 0 }}>
                                        Login Portal ACMT
                                    </h3>
                                    <p style={{ fontSize: 12, color: '#64748b', margin: '2px 0 0 0' }}>
                                        Pilih portal aktif & hubungkan sesi baca meter
                                    </p>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowModal(false)}
                                style={{
                                    background: 'transparent', border: 'none', borderRadius: 6,
                                    cursor: 'pointer', color: '#94a3b8', display: 'flex',
                                    alignItems: 'center', justifyContent: 'center', width: 32, height: 32
                                }}
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                            
                            {/* PILIHAN PORTAL: TOGGLE PILL */}
                            <div style={{
                                display: 'flex', background: '#f1f5f9',
                                padding: 3, borderRadius: 8, gap: 4
                            }}>
                                <button
                                    type="button"
                                    onClick={() => handleTabSwitch('new')}
                                    style={{
                                        flex: 1, padding: '8px 12px', border: 'none', borderRadius: 6,
                                        fontSize: 12, fontWeight: portalTab === 'new' ? 600 : 500,
                                        background: portalTab === 'new' ? '#ffffff' : 'transparent',
                                        color: portalTab === 'new' ? '#0f172a' : '#64748b',
                                        boxShadow: portalTab === 'new' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                                        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        gap: 6, transition: 'all 0.15s'
                                    }}
                                >
                                    <Zap size={14} color={portalTab === 'new' ? '#2563eb' : '#64748b'} />
                                    ACMT New (FSM)
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleTabSwitch('lama')}
                                    style={{
                                        flex: 1, padding: '8px 12px', border: 'none', borderRadius: 6,
                                        fontSize: 12, fontWeight: portalTab === 'lama' ? 600 : 500,
                                        background: portalTab === 'lama' ? '#ffffff' : 'transparent',
                                        color: portalTab === 'lama' ? '#0f172a' : '#64748b',
                                        boxShadow: portalTab === 'lama' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
                                        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        gap: 6, transition: 'all 0.15s'
                                    }}
                                >
                                    <Server size={14} color={portalTab === 'lama' ? '#2563eb' : '#64748b'} />
                                    ACMT Lama (IPAM)
                                </button>
                            </div>

                            {/* ================= PANEL ACMT NEW ================= */}
                            {portalTab === 'new' && (
                                <form onSubmit={handleLoginNew} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    {/* Header Info FSM */}
                                    <div style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        background: '#f8fafc', border: '1px solid #e2e8f0',
                                        padding: '10px 14px', borderRadius: 8
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                            <div style={{
                                                width: 32, height: 32, borderRadius: 6,
                                                background: '#eff6ff', border: '1px solid #dbeafe',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                color: '#2563eb'
                                            }}>
                                                <Zap size={16} />
                                            </div>
                                            <div>
                                                <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>
                                                    Field Service Management
                                                </div>
                                                <div style={{ fontSize: 11, color: '#64748b' }}>
                                                    Portal ACMT New (API 8088 / 8030)
                                                </div>
                                            </div>
                                        </div>
                                        <span style={{
                                            fontSize: 11, fontWeight: 600,
                                            color: hasNew ? '#15803d' : '#64748b',
                                            background: hasNew ? '#dcfce7' : '#f1f5f9',
                                            padding: '3px 8px', borderRadius: 4,
                                            border: `1px solid ${hasNew ? '#bbf7d0' : '#e2e8f0'}`,
                                            display: 'flex', alignItems: 'center', gap: 4
                                        }}>
                                            {hasNew ? <><CheckCircle2 size={12} /> Terhubung</> : <><Clock size={12} /> Belum Login</>}
                                        </span>
                                    </div>

                                    {/* Username */}
                                    <div>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: '#334155', display: 'block', marginBottom: 5 }}>
                                            Username
                                        </label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                type="text"
                                                value={userNew}
                                                onChange={e => setUserNew(e.target.value)}
                                                placeholder="Silahkan masukkan username"
                                                autoComplete="off"
                                                style={{
                                                    width: '100%', height: 38, padding: '0 12px 0 36px',
                                                    border: '1px solid #cbd5e1', borderRadius: 8,
                                                    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box'
                                                }}
                                            />
                                            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', display: 'flex' }}>
                                                <User size={15} />
                                            </span>
                                        </div>
                                    </div>

                                    {/* Password */}
                                    <div>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: '#334155', display: 'block', marginBottom: 5 }}>
                                            Password
                                        </label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                type={showPassNew ? 'text' : 'password'}
                                                value={passNew}
                                                onChange={e => setPassNew(e.target.value)}
                                                placeholder="Silahkan masukkan password"
                                                autoComplete="new-password"
                                                style={{
                                                    width: '100%', height: 38, padding: '0 36px 0 36px',
                                                    border: '1px solid #cbd5e1', borderRadius: 8,
                                                    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box'
                                                }}
                                            />
                                            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', display: 'flex' }}>
                                                <Lock size={15} />
                                            </span>
                                            <span
                                                onClick={() => setShowPassNew(p => !p)}
                                                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', cursor: 'pointer', display: 'flex' }}
                                                title="Lihat password"
                                            >
                                                {showPassNew ? <EyeOff size={15} /> : <Eye size={15} />}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Enkripsi */}
                                    <div>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: '#334155', display: 'block', marginBottom: 5 }}>
                                            Enkripsi
                                        </label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                type={showEnkripsiNew ? 'text' : 'password'}
                                                value={enkripsiNew}
                                                onChange={e => setEnkripsiNew(e.target.value)}
                                                placeholder="Silahkan masukkan enkripsi"
                                                autoComplete="new-password"
                                                style={{
                                                    width: '100%', height: 38, padding: '0 36px 0 36px',
                                                    border: '1px solid #cbd5e1', borderRadius: 8,
                                                    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box'
                                                }}
                                            />
                                            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', display: 'flex' }}>
                                                <Key size={15} />
                                            </span>
                                            <span
                                                onClick={() => setShowEnkripsiNew(p => !p)}
                                                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', cursor: 'pointer', display: 'flex' }}
                                                title="Lihat enkripsi"
                                            >
                                                {showEnkripsiNew ? <EyeOff size={15} /> : <Eye size={15} />}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Error Banner */}
                                    {errorNew && (
                                        <div style={{
                                            background: '#fef2f2', border: '1px solid #fee2e2',
                                            color: '#b91c1c', padding: '9px 12px', borderRadius: 8,
                                            fontSize: 12, fontWeight: 500, lineHeight: 1.4,
                                            display: 'flex', alignItems: 'center', gap: 8
                                        }}>
                                            <AlertCircle size={15} style={{ flexShrink: 0 }} />
                                            <span>{errorNew}</span>
                                        </div>
                                    )}

                                    {/* Tombol Login FSM */}
                                    <button
                                        type="submit"
                                        disabled={loading}
                                        style={{
                                            background: '#2563eb', color: '#ffffff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                            fontSize: 13, fontWeight: 600, padding: '10px 16px',
                                            borderRadius: 8, border: 'none', marginTop: 4,
                                            boxShadow: '0 1px 2px rgba(37, 99, 235, 0.2)',
                                            cursor: loading ? 'not-allowed' : 'pointer',
                                            opacity: loading ? 0.7 : 1
                                        }}
                                    >
                                        {loading ? (
                                            <>
                                                <RefreshCw size={15} className="animate-spin" />
                                                Memproses Login...
                                            </>
                                        ) : (
                                            <>
                                                <Zap size={15} />
                                                Login & Simpan Sesi Otomatis
                                            </>
                                        )}
                                    </button>

                                    <p style={{ fontSize: 11, color: '#64748b', textAlign: 'center', margin: 0, lineHeight: 1.4, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                                        <ShieldCheck size={13} color="#16a34a" />
                                        Sesi & token otomatis tersimpan langsung ke sistem begitu login berhasil.
                                    </p>
                                </form>
                            )}

                            {/* ================= PANEL ACMT LAMA ================= */}
                            {portalTab === 'lama' && (
                                <form onSubmit={handleLoginLama} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    {/* Header Info IPAM */}
                                    <div style={{
                                        background: '#f8fafc', border: '1px solid #e2e8f0',
                                        borderRadius: 8, padding: '10px 14px',
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                            <div style={{
                                                width: 32, height: 32, borderRadius: 6,
                                                background: '#eff6ff', border: '1px solid #dbeafe',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                color: '#2563eb'
                                            }}>
                                                <Server size={16} />
                                            </div>
                                            <div>
                                                <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>
                                                    Catat Meter Terpusat
                                                </div>
                                                <div style={{ fontSize: 11, color: '#64748b' }}>
                                                    Portal ACMT Lama (IPAM Server)
                                                </div>
                                            </div>
                                        </div>
                                        <span style={{
                                            fontSize: 11, fontWeight: 600,
                                            color: hasLama ? '#15803d' : '#64748b',
                                            background: hasLama ? '#dcfce7' : '#f1f5f9',
                                            padding: '3px 8px', borderRadius: 4,
                                            border: `1px solid ${hasLama ? '#bbf7d0' : '#e2e8f0'}`,
                                            display: 'flex', alignItems: 'center', gap: 4
                                        }}>
                                            {hasLama ? <><CheckCircle2 size={12} /> Terhubung</> : <><Clock size={12} /> Belum Login</>}
                                        </span>
                                    </div>

                                    {/* Username */}
                                    <div>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: '#334155', display: 'block', marginBottom: 5 }}>
                                            Username
                                        </label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                type="text"
                                                value={userLama}
                                                onChange={e => setUserLama(e.target.value)}
                                                placeholder="Silahkan masukkan username"
                                                autoComplete="off"
                                                style={{
                                                    width: '100%', height: 38, padding: '0 12px 0 36px',
                                                    border: '1px solid #cbd5e1', borderRadius: 8,
                                                    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box'
                                                }}
                                            />
                                            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', display: 'flex' }}>
                                                <User size={15} />
                                            </span>
                                        </div>
                                    </div>

                                    {/* Password */}
                                    <div>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: '#334155', display: 'block', marginBottom: 5 }}>
                                            Password
                                        </label>
                                        <div style={{ position: 'relative' }}>
                                            <input
                                                type={showPassLama ? 'text' : 'password'}
                                                value={passLama}
                                                onChange={e => setPassLama(e.target.value)}
                                                placeholder="Silahkan masukkan password"
                                                autoComplete="new-password"
                                                style={{
                                                    width: '100%', height: 38, padding: '0 36px 0 36px',
                                                    border: '1px solid #cbd5e1', borderRadius: 8,
                                                    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box'
                                                }}
                                            />
                                            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', display: 'flex' }}>
                                                <Lock size={15} />
                                            </span>
                                            <span
                                                onClick={() => setShowPassLama(p => !p)}
                                                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', cursor: 'pointer', display: 'flex' }}
                                                title="Lihat password"
                                            >
                                                {showPassLama ? <EyeOff size={15} /> : <Eye size={15} />}
                                            </span>
                                        </div>
                                    </div>

                                    {/* LIVE CAPTCHA */}
                                    <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                                            <label style={{ fontWeight: 600, fontSize: 12, color: '#334155' }}>
                                                Verifikasi CAPTCHA
                                            </label>
                                            <button
                                                type="button"
                                                onClick={() => fetchCaptcha(true)}
                                                style={{
                                                    background: 'none', border: 'none', fontSize: 12,
                                                    color: '#2563eb', cursor: 'pointer', fontWeight: 600,
                                                    display: 'flex', alignItems: 'center', gap: 4, padding: 0
                                                }}
                                            >
                                                <RefreshCw size={12} /> Ganti Gambar
                                            </button>
                                        </div>
                                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                            <div
                                                onClick={() => fetchCaptcha(true)}
                                                title="Klik untuk ganti gambar CAPTCHA"
                                                style={{
                                                    background: '#f8fafc', border: '1px solid #cbd5e1',
                                                    borderRadius: 8, padding: '4px 10px', display: 'flex',
                                                    alignItems: 'center', justifyContent: 'center',
                                                    minWidth: 145, height: 46, position: 'relative', cursor: 'pointer'
                                                }}
                                            >
                                                {loadingCaptcha ? (
                                                    <span style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                                                        <RefreshCw size={14} className="animate-spin" /> Memuat...
                                                    </span>
                                                ) : captchaB64 ? (
                                                    <img
                                                        src={captchaB64}
                                                        alt="CAPTCHA"
                                                        style={{ maxHeight: 38, borderRadius: 4, display: 'block' }}
                                                    />
                                                ) : (
                                                    <span style={{ fontSize: 12, color: '#ef4444', display: 'flex', alignItems: 'center', gap: 6 }}>
                                                        <AlertCircle size={14} /> Gagal memuat
                                                    </span>
                                                )}
                                            </div>
                                            <input
                                                type="text"
                                                value={captchaLama}
                                                onChange={e => setCaptchaLama(e.target.value)}
                                                placeholder="Ketik kode sesuai gambar"
                                                autoComplete="off"
                                                maxLength={6}
                                                style={{
                                                    flex: 1, height: 46, fontSize: 16, fontWeight: 700,
                                                    letterSpacing: 2, textAlign: 'center', border: '1px solid #cbd5e1',
                                                    borderRadius: 8, outline: 'none', background: '#ffffff',
                                                    color: '#0f172a', boxSizing: 'border-box'
                                                }}
                                            />
                                        </div>
                                        <p style={{ fontSize: 11, color: '#64748b', margin: '5px 0 0 0', display: 'flex', alignItems: 'center', gap: 5 }}>
                                            <Info size={13} color="#94a3b8" />
                                            Perhatikan huruf besar dan kecil (case-sensitive) sesuai gambar.
                                        </p>
                                    </div>

                                    {/* Error Banner */}
                                    {errorLama && (
                                        <div style={{
                                            background: '#fef2f2', border: '1px solid #fee2e2',
                                            color: '#b91c1c', padding: '9px 12px', borderRadius: 8,
                                            fontSize: 12, fontWeight: 500, lineHeight: 1.4,
                                            display: 'flex', alignItems: 'center', gap: 8
                                        }}>
                                            <AlertCircle size={15} style={{ flexShrink: 0 }} />
                                            <span>{errorLama}</span>
                                        </div>
                                    )}

                                    {/* Tombol Login IPAM */}
                                    <button
                                        type="submit"
                                        disabled={loading}
                                        style={{
                                            background: '#2563eb', color: '#ffffff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                            fontSize: 13, fontWeight: 600, padding: '10px 16px',
                                            borderRadius: 8, border: 'none', marginTop: 4,
                                            boxShadow: '0 1px 2px rgba(37, 99, 235, 0.2)',
                                            cursor: loading ? 'not-allowed' : 'pointer',
                                            opacity: loading ? 0.7 : 1
                                        }}
                                    >
                                        {loading ? (
                                            <>
                                                <RefreshCw size={15} className="animate-spin" />
                                                Memproses Login...
                                            </>
                                        ) : (
                                            <>
                                                <Zap size={15} />
                                                Login & Simpan Sesi Otomatis
                                            </>
                                        )}
                                    </button>



                                    <p style={{ fontSize: 11, color: '#64748b', textAlign: 'center', margin: 0, lineHeight: 1.4, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                                        <ShieldCheck size={13} color="#16a34a" />
                                        Sesi & cookies tersimpan langsung tanpa perlu pindah tab atau salin kode.
                                    </p>
                                </form>
                            )}

                        </div>

                        {/* Modal Footer */}
                        <div style={{
                            padding: '12px 20px',
                            borderTop: '1px solid #e2e8f0',
                            background: '#f8fafc',
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                        }}>
                            <button
                                type="button"
                                onClick={handleResetAll}
                                disabled={loading}
                                style={{
                                    color: '#ef4444', borderColor: '#fecaca',
                                    border: '1px solid #fecaca', background: '#fff',
                                    borderRadius: 8, fontSize: 12, padding: '7px 12px',
                                    cursor: 'pointer', fontWeight: 600,
                                    display: 'flex', alignItems: 'center', gap: 6
                                }}
                            >
                                <Trash2 size={13} />
                                Reset Semua Sesi
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowModal(false)}
                                style={{
                                    padding: '7px 18px', background: '#0f172a',
                                    color: '#fff', border: 'none', borderRadius: 8,
                                    fontSize: 12, fontWeight: 600, cursor: 'pointer'
                                }}
                            >
                                Tutup
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

function MultiSelectDropdown({ options, selected, onChange, placeholder }) {
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    useEffect(() => {
        function handleClickOutside(event) {
            if (ref.current && !ref.current.contains(event.target)) setOpen(false);
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <div 
                onClick={() => setOpen(!open)}
                style={{ ...inputStyle, width: 160, display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', whiteSpace: 'nowrap' }}
            >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', fontSize: 11, color: selected.length ? '#0f172a' : '#64748b' }}>
                    {selected.length === 0 ? placeholder : `${selected.length} LBKB Dipilih`}
                </span>
                <span style={{ fontSize: 9, color: '#94a3b8' }}>▼</span>
            </div>
            {open && (
                <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: 4, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 6, width: 240, maxHeight: 300, overflowY: 'auto', zIndex: 50, boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}>
                    <div style={{ padding: '8px 12px', borderBottom: '1px solid #f1f5f9', background: '#f8fafc', position: 'sticky', top: 0 }}>
                        <label style={{ fontSize: 11, display: 'flex', gap: 8, cursor: 'pointer', fontWeight: 600, color: '#374151', alignItems: 'center' }}>
                            <input 
                                type="checkbox" 
                                checked={selected.length === options.length && options.length > 0} 
                                onChange={(e) => onChange(e.target.checked ? [...options] : [])} 
                                style={{ margin: 0, cursor: 'pointer' }}
                            />
                            Pilih Semua
                        </label>
                    </div>
                    <div style={{ padding: '4px 0' }}>
                        {options.map(opt => (
                            <label key={opt} style={{ display: 'flex', gap: 8, padding: '6px 12px', fontSize: 11, cursor: 'pointer', color: '#475569', alignItems: 'center' }}>
                                <input 
                                    type="checkbox" 
                                    checked={selected.includes(opt)} 
                                    onChange={(e) => {
                                        if (e.target.checked) onChange([...selected, opt]);
                                        else onChange(selected.filter(x => x !== opt));
                                    }} 
                                    style={{ margin: 0, cursor: 'pointer' }}
                                />
                                {opt}
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

export default function VerifikasiPage() {
    useEffect(() => { document.title = "Verifikasi Data | METRIK" }, [])

    const { user, role } = useAuthStore()
    const qc = useQueryClient()

    const { data: reasons = [] } = useQuery({
        queryKey: ['reasons'],
        queryFn: () => api.get('/api/settings/reasons').then(r => r.data),
    })
    const { data: lbkbOptions = [] } = useQuery({
        queryKey: ['lbkb-options'],
        queryFn: () => api.get('/api/records/lbkb-options').then(r => r.data.options),
    })
    const [page, setPage] = useState(1)
    const [filter, setFilter] = useState({ status: '', search: '', anomalyOnly: false, merekMismatch: false, sessionId: '', unit: '', reasonType: '', lbkb: [], minSelisih: '', maxSelisih: '' })
    const [selected, setSelected] = useState(null)
    const [note, setNote] = useState('')
    const [reasonType, setReasonType] = useState('')
    const [correctedStand, setCorrectedStand] = useState('')
    const [activeFoto, setActiveFoto] = useState(null)   // { idpel, blth, fotoke, loading, url, error }
    const [expandedFoto, setExpandedFoto] = useState(null) // idpel yang sedang di-expand
    const [pendingAutoOpen, setPendingAutoOpen] = useState(false) // auto-buka record pertama setelah ganti page
    const [isOverrideMode, setIsOverrideMode] = useState(false)

    const blthList = getBlthList()

    const { data: sessions = [] } = useQuery({
        queryKey: ['sessions-list'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data)
    })

    // 1. Prioritas: bulan_verifikasi dari record yang sedang dibuka (jika ada)
    // 2. Fallback: bulan_verifikasi dari filter sesi, atau bulan kalender
    const selectedSession = sessions.find(s => String(s.id) === String(filter.sessionId))
    const activeBulan = (selected ? sessions.find(s => s.id === selected.session_id)?.bulan_verifikasi : null)
        || selectedSession?.bulan_verifikasi
        || blthList[0]

    const handleFotoClick = async (idpel, blth, fotoke) => {
        setActiveFoto({ idpel, blth, fotoke, loading: true, url: null, error: null, source: null })
        try {
            const token = useAuthStore.getState().token
            const resp = await fetch(
                `/api/foto?idpel=${encodeURIComponent(idpel)}&blth=${blth}&fotoke=${fotoke}`,
                { headers: { Authorization: `Bearer ${token}` } }
            )
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}))
                throw new Error(err.detail || `HTTP ${resp.status}`)
            }
            const photoSource = resp.headers.get('X-Photo-Source') || 'ACMT'
            const blob = await resp.blob()
            const url = URL.createObjectURL(blob)
            setActiveFoto(prev => ({ ...prev, loading: false, url, source: photoSource }))
        } catch (e) {
            const msg = e.message.includes('401') || e.message.includes('EXPIRED') || e.message.includes('belum diset')
                ? 'Sesi ACMT harus di input ulang'
                : e.message;
            setActiveFoto(prev => ({ ...prev, loading: false, error: msg }))
            if (msg.includes('input ulang')) toast.error(msg)
        }
    }

    const { data: records = [], isLoading } = useQuery({
        queryKey: ['records', page, filter],
        queryFn: () => api.get('/api/records/', {
            params: {
                skip: (page - 1) * 20,
                limit: 20,
                record_type: 'beda',   // Verifikasi hanya untuk data BEDA
                status: filter.status || undefined,
                search: filter.search || undefined,
                unit: filter.unit || undefined,
                reason_type: filter.reasonType || undefined,
                anomaly_only: filter.anomalyOnly,
                merek_mismatch: filter.merekMismatch,
                lbkb: filter.lbkb.length > 0 ? filter.lbkb.join(',') : undefined,
                min_selisih: filter.minSelisih !== '' && !isNaN(filter.minSelisih) ? Number(filter.minSelisih) : undefined,
                max_selisih: filter.maxSelisih !== '' && !isNaN(filter.maxSelisih) ? Number(filter.maxSelisih) : undefined,
                assigned_to: role === 'verifikator' ? user?.id : undefined,
                session_id: filter.sessionId || undefined
            }
        }).then(r => r.data),
    })

    // Auto-buka record pertama setelah pindah page (cross-page navigation)
    useEffect(() => {
        if (pendingAutoOpen && !isLoading && records.length > 0) {
            openModal(records[0])
            setPendingAutoOpen(false)
        } else if (pendingAutoOpen && !isLoading && records.length === 0) {
            // Tidak ada record lagi di page berikutnya
            setPendingAutoOpen(false)
            toast.success('Semua data di halaman ini sudah selesai dikerjakan!')
        }
    }, [records, isLoading, pendingAutoOpen])

    const verifyMutation = useMutation({
        mutationFn: ({ id, status, note, reasonType, correctedStand }) => api.patch(`/api/records/${id}`, {
            status,
            catatan: note,
            reason_type: reasonType || null,
            corrected_stand: correctedStand ? parseFloat(correctedStand) : null,
        }),
        onSuccess: (data, variables) => {
            toast.success('Data berhasil disimpan')
            qc.invalidateQueries(['records'])
            qc.invalidateQueries(['dashboard-stats'])

            const currentIndex = records.findIndex(r => r.id === variables.id)
            if (currentIndex !== -1 && currentIndex < records.length - 1) {
                // Ada record berikutnya di page ini, otomatis buka
                openModal(records[currentIndex + 1])
            } else if (currentIndex === records.length - 1 && records.length >= 20) {
                // Record terakhir di page ini, kemungkinan ada page berikutnya
                setSelected(null)
                setNote('')
                setReasonType('')
                setCorrectedStand('')
                setPage(p => p + 1)
                setPendingAutoOpen(true)
                toast.info('Lanjut ke halaman berikutnya...')
            } else {
                // Benar-benar record terakhir
                setSelected(null)
                setNote('')
                setReasonType('')
                setCorrectedStand('')
            }
        },
        onError: () => toast.error('Gagal menyimpan'),
    })

    const openModal = (r) => {
        setSelected(r)
        setNote(r.catatan || '')
        setReasonType(r.reason_type || '')
        setCorrectedStand(r.corrected_stand ?? '')
        setIsOverrideMode(false)
    }

    const navigateModal = (direction) => {
        if (!selected || records.length === 0) return
        const idx = records.findIndex(r => r.id === selected.id)
        if (idx === -1) return
        const newIdx = idx + direction
        if (newIdx >= 0 && newIdx < records.length) {
            openModal(records[newIdx])
        } else if (direction === 1 && idx === records.length - 1 && records.length >= 20) {
            // Record terakhir di page, coba lanjut ke page berikutnya
            setSelected(null)
            setPage(p => p + 1)
            setPendingAutoOpen(true)
        }
    }

    const handleVerify = (status) => {
        if (!reasonType) return toast.error('Pilih alasan terlebih dahulu')
        verifyMutation.mutate({ id: selected.id, status, note, reasonType, correctedStand })
    }

    const currentReasonObj = reasons.find(o => o.value === reasonType);
    const allowKoreksi = currentReasonObj?.requires_stand_correction || ['ai_salah_baca', 'foto_tidak_lurus'].includes(reasonType);

    const currentSelisih = selected && allowKoreksi && correctedStand !== '' && selected.stand_petugas != null
        ? Number(correctedStand) - Number(selected.stand_petugas)
        : (selected?.selisih ?? 0);

    const isSelisihZero = currentSelisih === 0;
    const selisihBg = isSelisihZero ? '#f0fdf4' : '#fef2f2';
    const selisihBorder = isSelisihZero ? '#bbf7d0' : '#fecaca';
    const selisihColor = isSelisihZero ? '#16a34a' : '#dc2626';

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            {/* Foto Meter Modal */}
            {activeFoto && <FotoModal foto={activeFoto} onClose={() => setActiveFoto(null)} />}
            {/* Header + Filters */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Verifikasi Data BEDA</h1>
                    <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Kerjakan data yang AI ≠ Biller — isi alasan dan koreksi jika perlu</p>
                </div>
                <div className="flex-filter">
                    <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#64748b', cursor: 'pointer', userSelect: 'none' }}>
                        <input type="checkbox" checked={filter.anomalyOnly} onChange={e => setFilter(f => ({ ...f, anomalyOnly: e.target.checked }))} style={{ accentColor: '#3b82f6' }} />
                        Anomali
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#64748b', cursor: 'pointer', userSelect: 'none' }}>
                        <input type="checkbox" checked={filter.merekMismatch} onChange={e => setFilter(f => ({ ...f, merekMismatch: e.target.checked }))} style={{ accentColor: '#3b82f6' }} />
                        Merek Beda
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#f8fafc', padding: '2px 6px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: 10, color: '#64748b', fontWeight: 600 }}>SELISIH:</span>
                        <input
                            type="number"
                            placeholder="Min"
                            value={filter.minSelisih}
                            onChange={e => { setFilter(f => ({ ...f, minSelisih: e.target.value })); setPage(1) }}
                            style={{ ...inputStyle, width: 55, height: 26, fontSize: 11, padding: '0 6px', border: '1px solid #cbd5e1', boxShadow: 'none' }}
                        />
                        <span style={{ fontSize: 11, color: '#94a3b8' }}>s/d</span>
                        <input
                            type="number"
                            placeholder="Max"
                            value={filter.maxSelisih}
                            onChange={e => { setFilter(f => ({ ...f, maxSelisih: e.target.value })); setPage(1) }}
                            style={{ ...inputStyle, width: 55, height: 26, fontSize: 11, padding: '0 6px', border: '1px solid #cbd5e1', boxShadow: 'none' }}
                        />
                    </div>
                    <input
                        placeholder="Cari ID Pelanggan..."
                        value={filter.search}
                        onChange={e => { setFilter(f => ({ ...f, search: e.target.value })); setPage(1) }}
                        style={{ ...inputStyle, width: 140 }}
                    />
                    <input
                        placeholder="Cari Unit UP..."
                        value={filter.unit}
                        onChange={e => { setFilter(f => ({ ...f, unit: e.target.value })); setPage(1) }}
                        style={{ ...inputStyle, width: 100 }}
                    />
                    <select
                        value={filter.sessionId}
                        onChange={e => { setFilter(f => ({ ...f, sessionId: e.target.value })); setPage(1) }}
                        style={{ ...inputStyle, paddingLeft: 10, maxWidth: 200 }}
                    >
                        <option value="">{role === 'verifikator' ? 'Semua Tugas Saya' : 'Semua Sesi'}</option>
                        {sessions.map(s => (
                            <option key={s.id} value={s.id}>
                                {s.batch_name ? s.batch_name : `Sesi #${s.id}`} ({new Date(s.created_at).toLocaleDateString('id-ID')})
                            </option>
                        ))}
                    </select>
                    <select
                        value={filter.status}
                        onChange={e => { setFilter(f => ({ ...f, status: e.target.value })); setPage(1) }}
                        style={{ ...inputStyle, paddingLeft: 10 }}
                    >
                        <option value="">Semua Status</option>
                        {Object.entries(STATUS_LABEL).map(([val, label]) => (
                            <option key={val} value={val}>{label}</option>
                        ))}
                    </select>
                    <select
                        value={filter.reasonType}
                        onChange={e => { setFilter(f => ({ ...f, reasonType: e.target.value })); setPage(1) }}
                        style={{ ...inputStyle, paddingLeft: 10, maxWidth: 160 }}
                    >
                        <option value="">Semua Alasan</option>
                        {reasons.map(r => (
                            <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                    </select>
                    <MultiSelectDropdown
                        options={lbkbOptions}
                        selected={filter.lbkb}
                        onChange={vals => { setFilter(f => ({ ...f, lbkb: vals })); setPage(1); }}
                        placeholder="Semua LBKB"
                    />
                </div>
            </div>

            {/* Panel Sesi ACMT */}
            <AcmtSessionPanel />

            {/* Modal */}
            {selected && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.45)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div className="photo-modal-content">

                        {/* Kiri: Foto Terbaru */}
                        <div className="photo-modal-left">
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                                Foto Terbaru
                                <span style={{ padding: '2px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', fontFamily: 'monospace' }}>
                                    {activeBulan.slice(0, 4)}/{activeBulan.slice(4)}
                                </span>
                                {!((selected ? sessions.find(s => s.id === selected.session_id)?.bulan_verifikasi : null) || selectedSession?.bulan_verifikasi) && (
                                    <span style={{ fontSize: 10, color: '#d97706' }} title="Batch ini diupload sebelum fitur kunci bulan, menggunakan bulan kalender sebagai fallback">⚠</span>
                                )}
                            </div>
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                                <LatestPhoto idpel={selected.id_pelanggan} blth={activeBulan} />
                            </div>

                            {/* Navigasi Next/Prev di bawah foto */}
                            <div style={{ display: 'flex', gap: 8, marginTop: 'auto' }}>
                                <button
                                    onClick={() => navigateModal(-1)}
                                    disabled={records.findIndex(r => r.id === selected.id) <= 0}
                                    style={{ flex: 1, padding: '8px 0', border: '1px solid #e2e8f0', borderRadius: 6, background: '#f8fafc', color: '#475569', fontSize: 12, fontWeight: 600, cursor: records.findIndex(r => r.id === selected.id) <= 0 ? 'not-allowed' : 'pointer', opacity: records.findIndex(r => r.id === selected.id) <= 0 ? 0.5 : 1 }}
                                >
                                    &larr; Sebelumnya
                                </button>
                                <button
                                    onClick={() => navigateModal(1)}
                                    disabled={records.findIndex(r => r.id === selected.id) >= records.length - 1 && records.length < 20}
                                    style={{ flex: 1, padding: '8px 0', border: '1px solid #e2e8f0', borderRadius: 6, background: '#f8fafc', color: '#475569', fontSize: 12, fontWeight: 600, cursor: (records.findIndex(r => r.id === selected.id) >= records.length - 1 && records.length < 20) ? 'not-allowed' : 'pointer', opacity: (records.findIndex(r => r.id === selected.id) >= records.length - 1 && records.length < 20) ? 0.5 : 1 }}
                                >
                                    {records.findIndex(r => r.id === selected.id) === records.length - 1 && records.length >= 20
                                        ? 'Hal. Berikutnya →'
                                        : 'Berikutnya →'}
                                </button>
                            </div>
                        </div>

                        {/* Kanan: Form Verifikasi */}
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                            {/* Modal Header */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                                <div>
                                    <h2 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: 0 }}>Kerjakan Data BEDA</h2>
                                    <p style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>ID Pelanggan: <strong>{selected.id_pelanggan}</strong></p>
                                </div>
                                <button onClick={() => setSelected(null)} style={{ background: '#f1f5f9', border: 'none', borderRadius: 6, width: 28, height: 28, cursor: 'pointer', fontSize: 14, color: '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>×</button>
                            </div>

                            {/* Mode QA / Read-Only Check */}
                            {(() => {
                                const isAlreadyVerified = selected?.status !== 'PENDING';
                                const isSupervisor = role !== 'verifikator';
                                const isReadOnly = isAlreadyVerified && !isOverrideMode;

                                return (
                                    <>
                                        {/* Side-by-side data */}
                                        <div className="grid-upload" style={{ marginBottom: 16 }}>
                                            {[
                                                { title: 'Hasil AI', bg: '#f8fafc', border: '#e2e8f0', stand: selected.stand_ai, merek: selected.merek_ai, tipe: selected.tipe_ai },
                                                { title: 'Stand Biller', bg: '#fffbeb', border: '#fde68a', stand: selected.stand_petugas, merek: selected.merek_petugas, tipe: selected.tipe_petugas },
                                            ].map(col => (
                                                <div key={col.title} style={{ background: col.bg, border: `1px solid ${col.border}`, borderRadius: 8, padding: 14 }}>
                                                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 12 }}>{col.title}</div>
                                                    {[['Stand KWH', col.stand], ['Merek', col.merek], ['Tipe', col.tipe]].map(([k, v]) => (
                                                        <div key={k} style={{ marginBottom: 8 }}>
                                                            <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 2 }}>{k}</div>
                                                            <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                                                                {k === 'Stand KWH' && col.title === 'Hasil AI' && allowKoreksi && correctedStand !== '' ? (
                                                                    <span>
                                                                        <span style={{ color: '#16a34a' }}>{correctedStand}</span>
                                                                        <span style={{ textDecoration: 'line-through', color: '#94a3b8', fontSize: 11, marginLeft: 6 }}>{v ?? '—'}</span>
                                                                    </span>
                                                                ) : (
                                                                    v ?? '—'
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            ))}
                                        </div>

                                        {selected.lbkb && selected.lbkb !== 'NORMAL' && (
                                            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 16 }}>
                                                <div style={{ fontSize: 10, fontWeight: 700, color: '#dc2626', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 4 }}>Informasi LBKB</div>
                                                <div style={{ fontSize: 13, fontWeight: 600, color: '#991b1b' }}>{selected.lbkb}</div>
                                            </div>
                                        )}

                                        {/* Selisih */}
                                        <div style={{ background: selisihBg, border: `1px solid ${selisihBorder}`, borderRadius: 8, padding: '12px 16px', marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'all 0.2s' }}>
                                            <div>
                                                <div style={{ fontSize: 10, color: '#94a3b8', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Selisih Stand</div>
                                                <div style={{ fontSize: 20, fontWeight: 700, color: selisihColor, transition: 'color 0.2s' }}>
                                                    {currentSelisih} KWH
                                                </div>
                                            </div>
                                            {selected.is_anomaly && (
                                                <span style={{ padding: '4px 10px', background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca', borderRadius: 5, fontSize: 11, fontWeight: 600 }}>
                                                    ⚠ Anomali Tinggi
                                                </span>
                                            )}
                                        </div>

                                        {/* Alasan */}
                                        <div style={{ marginBottom: 14 }}>
                                            <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                                                Alasan Perbedaan <span style={{ color: '#ef4444' }}>*</span>
                                            </label>
                                            <select
                                                value={reasonType}
                                                onChange={e => setReasonType(e.target.value)}
                                                disabled={isReadOnly}
                                                style={{ ...inputStyle, width: '100%', height: 36, paddingLeft: 11, boxSizing: 'border-box', background: isReadOnly ? '#f8fafc' : '#fff', opacity: isReadOnly ? 0.7 : 1 }}
                                            >
                                                <option value="">— Pilih Alasan —</option>
                                                {reasons.filter(r => r.is_active || r.value === reasonType).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                            </select>
                                        </div>

                                        {/* Stand koreksi (muncul jika alasan mengizinkan) */}
                                        {allowKoreksi && (
                                            <div style={{ marginBottom: 14 }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                                    <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block' }}>
                                                        Stand Koreksi (KWH)
                                                    </label>
                                                    <button
                                                        type="button"
                                                        onClick={() => setCorrectedStand(selected.stand_petugas != null ? String(selected.stand_petugas) : '')}
                                                        disabled={isReadOnly || selected.stand_petugas == null}
                                                        style={{ 
                                                            fontSize: 10, padding: '2px 8px', borderRadius: 4, border: '1px solid #cbd5e1', 
                                                            background: '#f8fafc', color: '#475569', fontWeight: 600,
                                                            cursor: (isReadOnly || selected.stand_petugas == null) ? 'not-allowed' : 'pointer',
                                                            display: 'flex', alignItems: 'center', gap: 4, opacity: (isReadOnly || selected.stand_petugas == null) ? 0.5 : 1,
                                                            transition: 'background 0.2s'
                                                        }}
                                                        onMouseEnter={e => !isReadOnly && (e.currentTarget.style.background = '#e2e8f0')}
                                                        onMouseLeave={e => !isReadOnly && (e.currentTarget.style.background = '#f8fafc')}
                                                    >
                                                        Stan Biller
                                                    </button>
                                                </div>
                                                <input
                                                    type="number"
                                                    value={correctedStand}
                                                    onChange={e => setCorrectedStand(e.target.value)}
                                                    disabled={isReadOnly}
                                                    placeholder="Masukkan stand yang benar..."
                                                    style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', background: isReadOnly ? '#f8fafc' : '#fff', opacity: isReadOnly ? 0.7 : 1 }}
                                                />
                                            </div>
                                        )}

                                        {/* Catatan */}
                                        <div style={{ marginBottom: 20 }}>
                                            <label style={{ fontSize: 12, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                                                Catatan <span style={{ color: '#94a3b8', fontWeight: 400 }}>(opsional)</span>
                                            </label>
                                            <textarea
                                                value={note} onChange={e => setNote(e.target.value)}
                                                disabled={isReadOnly}
                                                rows={2}
                                                placeholder="Catatan tambahan..."
                                                style={{ width: '100%', padding: 10, border: '1px solid #d1d5db', borderRadius: 7, fontSize: 12, outline: 'none', resize: 'none', boxSizing: 'border-box', color: '#1e293b', background: isReadOnly ? '#f8fafc' : '#fff', opacity: isReadOnly ? 0.7 : 1 }}
                                            />
                                        </div>

                                        {/* Action buttons */}
                                        {isReadOnly ? (
                                            <div style={{ marginTop: 'auto', marginBottom: 0, padding: 16, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', textAlign: 'center' }}>
                                                <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
                                                    Data ini telah selesai diverifikasi.
                                                </div>
                                                {isSupervisor ? (
                                                    <button onClick={() => setIsOverrideMode(true)} style={{ ...btnBase, background: '#dc2626', color: '#fff' }}>
                                                        Anulir / Revisi Keputusan
                                                    </button>
                                                ) : (
                                                    <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}> Data Terkunci</div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="grid-upload" style={{ marginTop: 'auto', marginBottom: 0 }}>
                                                <button onClick={() => handleVerify('VERIFIED_OK')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#16a34a', color: '#fff' }}>{isOverrideMode ? 'Simpan Revisi' : '✓ Selesai / OK'}</button>
                                                <button onClick={() => handleVerify('NEED_INVESTIGATION')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#d97706', color: '#fff' }}>{isOverrideMode ? 'Ubah ke Investigasi' : '⚑ Perlu Investigasi'}</button>
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>
                    </div>
                </div>
            )}

            {/* Table */}
            <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                {isLoading ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Memuat data...</div>
                ) : (
                    <div className="table-responsive">
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                                <tr style={{ background: '#f8fafc' }}>
                                    {[
    { label: 'Unit', icon: Building2 },
    { label: 'ID Pelanggan', icon: Hash },
    { label: 'Biller', icon: FileText },
    { label: 'Stand AI', icon: Bot, iconColor: '#6366f1' },
    { label: 'Stand Biller', icon: User, iconColor: '#f59e0b' },
    { label: 'Selisih', icon: ArrowUpDown },
    { label: 'Merek', icon: Layers },
    { label: 'LBKB', icon: Tag },
    { label: 'Alasan', icon: Info },
    { label: 'Status', icon: CheckCircle2 },
    { label: 'Foto', icon: Camera },
    { label: 'Aksi', icon: Sparkles, iconColor: '#4f46e5' }
].map(h => (
    <th key={h.label} style={{ padding: '11px 14px', textAlign: 'left', color: '#475569', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <h.icon size={12} style={{ color: h.iconColor || '#64748b' }} />
            {h.label}
        </span>
    </th>
))}
                                </tr>
                            </thead>
                            <tbody>
                                {records.map(r => (
                                    <tr key={r.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '10px 16px', color: '#64748b', fontSize: 11 }}>{r.unit || '—'}</td>
                                        <td style={{ padding: '10px 16px', fontWeight: 600, color: '#0f172a' }}>{r.id_pelanggan}</td>
                                        <td style={{ padding: '10px 16px', color: '#64748b', fontSize: 11 }}>{r.kode_nama_biller || '—'}</td>
                                        <td style={{ padding: '10px 16px', color: '#374151' }}>
                                            {r.corrected_stand != null ? (
                                                <span>
                                                    <span style={{ color: '#16a34a', fontWeight: 600 }}>{r.corrected_stand}</span>
                                                    <span style={{ textDecoration: 'line-through', color: '#94a3b8', fontSize: 11, marginLeft: 6 }}>{r.stand_ai}</span>
                                                </span>
                                            ) : (r.stand_ai ?? '—')}
                                        </td>
                                        <td style={{ padding: '10px 16px', color: '#374151' }}>{r.stand_petugas ?? '—'}</td>
                                        <td style={{ padding: '10px 16px', fontWeight: 600, color: (r.corrected_stand != null && r.stand_petugas != null ? Number(r.corrected_stand) - Number(r.stand_petugas) : (r.selisih || 0)) !== 0 ? '#dc2626' : '#16a34a' }}>
                                            {r.corrected_stand != null && r.stand_petugas != null ? Number(r.corrected_stand) - Number(r.stand_petugas) : (r.selisih ?? '—')}
                                        </td>
                                        <td style={{ padding: '10px 16px', color: '#64748b' }}>{r.merek_ai || '—'} / {r.merek_petugas || '—'}</td>
                                        <td style={{ padding: '10px 16px', color: (r.lbkb && r.lbkb !== 'NORMAL') ? '#dc2626' : '#64748b', fontWeight: (r.lbkb && r.lbkb !== 'NORMAL') ? 600 : 400, fontSize: 11 }}>{r.lbkb || '—'}</td>
                                        <td style={{ padding: '10px 16px', color: '#64748b', fontSize: 11 }}>
                                            {r.reason_type
                                                ? reasons.find(o => o.value === r.reason_type)?.label || r.reason_type
                                                : <span style={{ color: '#cbd5e1' }}>—</span>}
                                        </td>
                                        <td style={{ padding: '10px 16px' }}><Badge status={r.status} /></td>
                                        {/* Kolom Foto */}
                                        <td style={{ padding: '10px 16px', minWidth: 120 }}>
                                            <button
                                                onClick={() => setExpandedFoto(expandedFoto === r.id_pelanggan ? null : r.id_pelanggan)}
                                                style={{
                                                    background: expandedFoto === r.id_pelanggan ? '#dbeafe' : '#f1f5f9',
                                                    color: '#1d4ed8', border: '1px solid #bfdbfe', borderRadius: 5,
                                                    padding: '4px 10px', cursor: 'pointer', fontSize: 11, fontWeight: 500,
                                                    display: 'inline-flex', alignItems: 'center', gap: 5
                                                }}
                                            >
                                                <Camera size={12} /> Foto
                                            </button>
                                            {expandedFoto === r.id_pelanggan && (
                                                <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 3 }}>
                                                    {blthList.map(blth =>
                                                        Array.from({ length: FOTO_PER_MONTH }, (_, i) => i + 1).map(fk => (
                                                            <button
                                                                key={`${blth}-${fk}`}
                                                                onClick={() => handleFotoClick(r.id_pelanggan, blth, String(fk))}
                                                                style={{
                                                                    background: '#fff', border: '1px solid #e2e8f0',
                                                                    borderRadius: 4, padding: '3px 8px', cursor: 'pointer',
                                                                    fontSize: 10, color: '#374151', textAlign: 'left',
                                                                    whiteSpace: 'nowrap'
                                                                }}
                                                            >
                                                                PHOTO {fk} - {blth}
                                                            </button>
                                                        ))
                                                    )}
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ padding: '10px 16px' }}>
                                            <button
                                                onClick={() => openModal(r)}
                                                style={{ background: '#f1f5f9', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 5, padding: '4px 12px', cursor: 'pointer', fontSize: 11, fontWeight: 500 }}
                                            >
                                                Kerjakan
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {records.length === 0 && (
                                    <tr><td colSpan={8} style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Tidak ada data BEDA yang perlu dikerjakan</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Pagination */}
                <div style={{ padding: '10px 16px', borderTop: '1px solid #f1f5f9', display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'flex-end' }}>
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                        style={{ padding: '4px 12px', border: '1px solid #e2e8f0', borderRadius: 5, cursor: page === 1 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, color: '#374151', opacity: page === 1 ? 0.4 : 1 }}>
                        Sebelumnya
                    </button>
                    <span style={{ color: '#64748b', fontSize: 12 }}>Hal. {page}</span>
                    <button onClick={() => setPage(p => p + 1)} disabled={records.length < 20}
                        style={{ padding: '4px 12px', border: '1px solid #e2e8f0', borderRadius: 5, cursor: records.length < 20 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, color: '#374151', opacity: records.length < 20 ? 0.4 : 1 }}>
                        Berikutnya
                    </button>
                </div>
            </div>
        </div>
    )
}