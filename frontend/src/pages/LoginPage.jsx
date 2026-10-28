import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../api/axios'
import { toast } from 'sonner'
import logoImg from '../assets/logo.png'

export default function LoginPage() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const { setAuth } = useAuthStore()
    const navigate = useNavigate()

    useEffect(() => {
        document.title = "Login | METRIK"
    }, [])

    async function handleLogin(e) {
        e.preventDefault()
        setLoading(true)
        try {
            const res = await api.post('/api/auth/login', { username, password })
            setAuth(res.data.role, res.data.full_name, res.data.kode_unit)
            toast.success(`Selamat datang, ${res.data.full_name}!`)
            navigate('/')
        } catch (err) {
            if (err.response && err.response.status === 429) {
                toast.error('Terlalu banyak percobaan! Anda diblokir sementara, coba lagi nanti.')
            } else if (err.response && err.response.data && err.response.data.detail) {
                toast.error(err.response.data.detail)
            } else {
                toast.error('Username atau password salah!')
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bg-mesh" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', boxSizing: 'border-box' }}>
            <div className="animate-slide-up login-card-wrapper">
                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <img src={logoImg} alt="Logo" style={{ height: 120, width: 'auto', objectFit: 'contain', display: 'block', margin: '0 auto 12px' }} />
                    <div style={{ fontSize: 28, fontWeight: 'bold', color: '#ffffff', letterSpacing: '1px', marginBottom: 4 }}>METRIK</div>
                    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.9)', margin: 0, fontWeight: 500, letterSpacing: '0.5px' }}>Sistem Verifikasi KWH Meter</p>
                </div>

                {/* Card */}
                <div className="glass" style={{ borderRadius: 16, padding: '36px 32px', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
                    <form onSubmit={handleLogin}>
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1e293b', display: 'block', marginBottom: 8, letterSpacing: '0.3px' }}>Username</label>
                            <input
                                type="text" value={username} onChange={e => setUsername(e.target.value)}
                                placeholder="Masukkan username"
                                style={{ width: '100%', height: 44, padding: '0 14px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.8)', borderRadius: 8, outline: 'none', fontSize: 14, color: '#1e293b', boxSizing: 'border-box', transition: 'all 0.2s', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' }}
                                onFocus={e => { e.target.style.borderColor = '#3b82f6'; e.target.style.background = '#fff'; e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.2)'; }}
                                onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.8)'; e.target.style.background = 'rgba(255,255,255,0.6)'; e.target.style.boxShadow = 'inset 0 2px 4px rgba(0,0,0,0.02)'; }}
                                required
                            />
                        </div>
                        <div style={{ marginBottom: 28, position: 'relative' }}>
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1e293b', display: 'block', marginBottom: 8, letterSpacing: '0.3px' }}>Password</label>
                            <input
                                type={showPassword ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)}
                                placeholder="Masukkan password"
                                style={{ width: '100%', height: 44, padding: '0 40px 0 14px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.8)', borderRadius: 8, outline: 'none', fontSize: 14, color: '#1e293b', boxSizing: 'border-box', transition: 'all 0.2s', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' }}
                                onFocus={e => { e.target.style.borderColor = '#3b82f6'; e.target.style.background = '#fff'; e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.2)'; }}
                                onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.8)'; e.target.style.background = 'rgba(255,255,255,0.6)'; e.target.style.boxShadow = 'inset 0 2px 4px rgba(0,0,0,0.02)'; }}
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute', right: 10, top: 32, height: 24, width: 24,
                                    background: 'transparent', border: 'none', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b'
                                }}
                            >
                                {showPassword ? (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                                ) : (
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                )}
                            </button>
                        </div>
                        <button
                            type="submit" disabled={loading}
                            className="btn-primary"
                            style={{ width: '100%', height: 44, border: 'none', borderRadius: 8, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 14, letterSpacing: '0.2px', opacity: loading ? 0.7 : 1 }}
                        >
                            {loading ? 'Memproses...' : 'Masuk ke Aplikasi'}
                        </button>
                    </form>
                </div>

            </div>
        </div>
    )
}