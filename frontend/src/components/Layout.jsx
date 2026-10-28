import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore, canAccess } from '../store/authStore'
import NotificationBell from './NotificationBell'
import logoImg from '../assets/logo.png'

// Semua menu yang ada — visibilitas dikontrol oleh canAccess(role, menu)
const navItems = [
    { to: '/',           label: 'Dashboard',        exact: true, menu: 'dashboard' },
    { to: '/upload',     label: 'Upload Match & Beda',            menu: 'upload' },
    { to: '/verifikasi', label: 'Verifikasi Data',                menu: 'verifikasi' },
    { to: '/assignment', label: 'Pembagian Tugas',                menu: 'pembagian' },
    { to: '/progress',   label: 'Progres Operator',              menu: 'progres' },
    { to: '/export',     label: 'Export Excel',                   menu: 'export' },
    { to: '/audit',      label: 'Audit Trail',                    menu: 'audit' },
    { to: '/users',      label: 'Pengaturan',                     menu: 'settings' },
]

// Label role yang ditampilkan di sidebar
const ROLE_LABEL = {
    super_admin: 'Super Admin',
    uid:         'UID',
    up3:         'UP3',
    ulp:         'ULP',
    verifikator: 'Verifikator',
}

export default function Layout() {
    const { user, role, kode_unit, logout } = useAuthStore()
    const fullName = user?.full_name
    const navigate = useNavigate()
    const location = useLocation()
    const queryClient = useQueryClient()
    const [isSidebarOpen, setIsSidebarOpen] = useState(false)
    const [dialog, setDialog] = useState(null)

    function handleLogout() {
        setDialog({
            title: 'Keluar',
            message: 'Apakah Anda yakin ingin keluar dari aplikasi?',
            onConfirm: async () => {
                try {
                    // Import api secara dinamis untuk menghindari circular dependency
                    const api = (await import('../api/axios')).default
                    await api.post('/api/auth/logout')
                } catch (e) {
                    console.error("Gagal logout di backend:", e)
                }
                queryClient.clear() // Bersihkan semua cache React Query agar data user lama hilang
                logout()
                navigate('/login')
            }
        })
    }

    const initials = fullName ? fullName.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : 'U'
    const activeLabel = navItems.find(i => i.to === location.pathname)?.label || 'Aplikasi'

    return (
        <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
            {dialog && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ background: '#fff', borderRadius: 10, width: 360, maxWidth: '90%', padding: 24, boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
                        <h3 style={{ margin: '0 0 12px 0', fontSize: 16, color: '#0f172a' }}>{dialog.title}</h3>
                        <p style={{ margin: '0 0 20px 0', fontSize: 13, color: '#475569', lineHeight: 1.5 }}>{dialog.message}</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={() => setDialog(null)} style={{ padding: '8px 16px', background: '#f1f5f9', color: '#475569', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>Batal</button>
                            <button onClick={() => { dialog.onConfirm(); setDialog(null) }} style={{ padding: '8px 16px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
                                Ya, Keluar
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Mobile Backdrop */}
            {isSidebarOpen && (
                <div onClick={() => setIsSidebarOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9 }}></div>
            )}
            
            {/* Sidebar */}
            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`} style={{ width: 'var(--sidebar-w)', display: 'flex', flexDirection: 'column', flexShrink: 0, zIndex: 10 }}>
                <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', position: 'relative' }}>
                    <button className="sidebar-close-btn" onClick={() => setIsSidebarOpen(false)} style={{ position: 'absolute', top: 12, right: 12, background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', fontSize: 20, cursor: 'pointer', padding: 4 }}>✕</button>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <img src={logoImg} alt="Logo" style={{ height: 80, width: 'auto', objectFit: 'contain', display: 'block', marginBottom: 8 }} />
                        <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ffffff', letterSpacing: '1px', marginBottom: 4 }}>METRIK</div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', letterSpacing: '0.5px', textTransform: 'uppercase', textAlign: 'center', fontWeight: 500 }}>Sistem Verifikasi KWH Meter</div>
                        <div style={{ fontSize: 9, color: 'rgba(96,165,250,0.8)', letterSpacing: '1px', marginTop: 8, fontWeight: 700, padding: '2px 6px', background: 'rgba(59,130,246,0.1)', borderRadius: 4, border: '1px solid rgba(59,130,246,0.2)' }}>v1.2.0</div>
                    </div>
                </div>

                <nav style={{ flex: 1, padding: '12px 8px', overflowY: 'auto' }}>
                    {navItems.map(item => {
                        if (!canAccess(role, item.menu)) return null
                        return (
                            <NavLink
                                key={item.to} to={item.to}
                                end={item.exact}
                                onClick={() => setIsSidebarOpen(false)}
                                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                                style={{ borderRadius: 6 }}
                            >
                                {item.label}
                            </NavLink>
                        )
                    })}
                </nav>

                <div style={{ padding: '16px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(0,0,0,0.1)' }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(6,182,212,0.2))', border: '1px solid rgba(59,130,246,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600, color: '#60a5fa', flexShrink: 0 }}>
                        {initials}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, color: '#fff', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fullName}</div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{ROLE_LABEL[role] || role}{kode_unit ? ` · ${kode_unit}` : ''}</div>
                    </div>
                    <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: 11, fontWeight: 500, transition: 'color 0.2s' }} onMouseOver={e => e.target.style.color = '#ef4444'} onMouseOut={e => e.target.style.color = 'rgba(255,255,255,0.4)'} title="Logout">Keluar</button>
                </div>
            </div>

            {/* Main */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
                {/* Topbar */}
                <div className="topbar-glass" style={{ height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px', flexShrink: 0, position: 'sticky', top: 0, zIndex: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <button className="mobile-menu-btn" onClick={() => setIsSidebarOpen(true)}>☰</button>
                        <div style={{ fontSize: 15, fontWeight: 600, color: '#1e293b', letterSpacing: '-0.2px' }}>{activeLabel}</div>
                    </div>
                    <NotificationBell />
                </div>

                <div className="animate-fade-in" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: 28, flex: 1 }}>
                        <Outlet />
                    </div>
                    <footer style={{ padding: '16px 28px', borderTop: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 12, textAlign: 'center', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>&copy; {new Date().getFullYear()} METRIK PT PLN (Persero) UP3 Tanjung Karang &mdash; Sistem Verifikasi KWH Meter. All rights reserved.</span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>Versi 1.2.0</span>
                    </footer>
                </div>
            </div>
        </div>
    )
}