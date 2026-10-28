import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'
import { toast } from 'sonner'
import { useAuthStore } from '../store/authStore'

const selectStyle = { width: '100%', height: 36, padding: '0 11px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, outline: 'none', color: '#1e293b', boxSizing: 'border-box' }

export default function ExportPage() {
    useEffect(() => { document.title = "Export | METRIK" }, [])

    const { role } = useAuthStore()
    const [loading, setLoading] = useState(false)
    const [exportMode, setExportMode] = useState('sesi')
    const [filter, setFilter] = useState({ status: '', session_id: '', record_type: '', bulan: '' })

    const { data: sessions = [] } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const uniqueBulan = useMemo(() => {
        if (!sessions) return []
        const bln = sessions.map(s => s.bulan_verifikasi).filter(Boolean)
        return [...new Set(bln)].sort((a, b) => b.localeCompare(a))
    }, [sessions])

    const formatBulan = (val) => {
        if (!val || val.length !== 6) return val
        const y = val.substring(0, 4)
        const m = val.substring(4, 6)
        const months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        return `${months[parseInt(m) - 1] || m} ${y}`
    }

    async function handleExport() {
        if (exportMode === 'sesi' && !filter.session_id) return toast.error('Pilih sesi terlebih dahulu')
        if (exportMode === 'bulan' && !filter.bulan) return toast.error('Pilih bulan terlebih dahulu')
        
        setLoading(true)
        try {
            const params = {
                filter_status: filter.status || 'all',
                record_type: filter.record_type || 'all',
            }
            if (exportMode === 'sesi') params.session_id = filter.session_id;
            if (exportMode === 'bulan') params.bulan = filter.bulan;

            const res = await api.get('/api/export/', {
                params,
                responseType: 'blob',
            })
            const url = URL.createObjectURL(res.data)
            const a = document.createElement('a')
            a.href = url
            const tipe = filter.record_type ? `_${filter.record_type}` : ''
            const identifier = exportMode === 'sesi' ? `sesi${filter.session_id}` : `bulan${filter.bulan}`
            a.download = `hasil_final${tipe}_${identifier}_${new Date().toISOString().slice(0, 10)}.xlsx`
            a.click()
            URL.revokeObjectURL(url)
            toast.success('File berhasil didownload')
        } catch {
            toast.error('Gagal export data')
        } finally {
            setLoading(false)
        }
    }

    if (!['super_admin', 'uid', 'up3', 'ulp'].includes(role)) return <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Akses ditolak.</div>

    const selectedSession = sessions.find(s => String(s.id) === String(filter.session_id))

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            {loading && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(255,255,255,0.8)', zIndex: 99999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(3px)' }}>
                    <div style={{ width: 40, height: 40, border: '4px solid #cbd5e1', borderTopColor: '#0f172a', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                    <div style={{ marginTop: 20, fontSize: 16, fontWeight: 600, color: '#0f172a' }}>Sedang Menggabungkan & Mengunduh Excel...</div>
                    <div style={{ marginTop: 8, fontSize: 13, color: '#64748b', maxWidth: 400, textAlign: 'center', lineHeight: 1.5 }}>Data yang besar mungkin memakan waktu hingga beberapa menit. Mohon JANGAN tutup atau pindah halaman ini.</div>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
            )}
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Export Excel</h1>
                <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Download hasil verifikasi: gabungan data Match + Beda dalam format .xlsx</p>
            </div>

            <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: 24, maxWidth: 500 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 18 }}>Parameter Export</div>

                {/* Mode Selector */}
                <div style={{ marginBottom: 14 }}>
                    <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5, fontWeight: 500 }}>Mode Export</label>
                    <div style={{ display: 'flex', gap: 10 }}>
                        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                            <input type="radio" name="mode" checked={exportMode === 'sesi'} onChange={() => setExportMode('sesi')} />
                            Berdasarkan Sesi
                        </label>
                        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                            <input type="radio" name="mode" checked={exportMode === 'bulan'} onChange={() => setExportMode('bulan')} />
                            {['uid', 'super_admin'].includes(role) ? 'Keseluruhan Provinsi (Per Bulan)' : role === 'up3' ? 'Seluruh ULP di UP3 Ini (Per Bulan)' : 'Semua Data ULP Ini (Per Bulan)'}
                        </label>
                    </div>
                </div>

                {/* Session / Bulan selector */}
                {exportMode === 'sesi' ? (
                <div style={{ marginBottom: 14 }}>
                    <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5, fontWeight: 500 }}>Sesi Upload</label>
                    <select value={filter.session_id} onChange={e => setFilter(f => ({ ...f, session_id: e.target.value }))} style={selectStyle}>
                        <option value="">Pilih sesi...</option>
                        {sessions.filter(s => s.status === 'done').map(s => (
                            <option key={s.id} value={s.id}>
                                {s.batch_name ? s.batch_name : `Sesi #${s.id}`} — {s.file_match_name || s.file_beda_name} ({s.total_match?.toLocaleString() ?? 0} match, {s.total_beda?.toLocaleString() ?? 0} beda)
                            </option>
                        ))}
                    </select>
                </div>
                ) : (
                <div style={{ marginBottom: 14 }}>
                    <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5, fontWeight: 500 }}>Pilih Bulan</label>
                    <select value={filter.bulan} onChange={e => setFilter(f => ({ ...f, bulan: e.target.value }))} style={selectStyle}>
                        <option value="">Pilih bulan...</option>
                        {uniqueBulan.map(b => (
                            <option key={b} value={b}>{formatBulan(b)}</option>
                        ))}
                    </select>
                </div>
                )}

                {/* Summary card */}
                {selectedSession && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                        {[
                            { label: 'Total', val: selectedSession.total_records, color: '#374151', bg: '#f8fafc', border: '#e2e8f0' },
                            { label: 'Match', val: selectedSession.total_match, color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
                            { label: 'Beda', val: selectedSession.total_beda, color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
                        ].map(({ label, val, color, bg, border }) => (
                            <div key={label} style={{ background: bg, border: `1px solid ${border}`, borderRadius: 7, padding: '10px 14px', textAlign: 'center' }}>
                                <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4 }}>{label}</div>
                                <div style={{ fontSize: 18, fontWeight: 700, color }}>{val?.toLocaleString() ?? '—'}</div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Record type filter */}
                <div style={{ marginBottom: 14 }}>
                    <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5, fontWeight: 500 }}>Tipe Data</label>
                    <select value={filter.record_type} onChange={e => setFilter(f => ({ ...f, record_type: e.target.value }))} style={selectStyle}>
                        <option value="">Semua (Match + Beda)</option>
                        <option value="match">Match Saja</option>
                        <option value="beda">Beda Saja</option>
                    </select>
                </div>

                {/* Status filter */}
                <div style={{ marginBottom: 24 }}>
                    <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5, fontWeight: 500 }}>Filter Status</label>
                    <select value={filter.status} onChange={e => setFilter(f => ({ ...f, status: e.target.value }))} style={selectStyle}>
                        <option value="">Semua Status</option>
                        <option value="VERIFIED_OK">Selesai / OK</option>
                        <option value="VERIFIED_REJECT">Tolak</option>
                        <option value="NEED_INVESTIGATION">Investigasi</option>
                        <option value="PENDING">Pending</option>
                    </select>
                </div>

                <button
                    onClick={handleExport}
                    disabled={loading || (exportMode === 'sesi' && !filter.session_id) || (exportMode === 'bulan' && !filter.bulan)}
                    style={{
                        background: '#0f172a', color: '#fff', border: 'none', borderRadius: 7,
                        padding: '10px 24px', cursor: loading || (exportMode === 'sesi' && !filter.session_id) || (exportMode === 'bulan' && !filter.bulan) ? 'not-allowed' : 'pointer',
                        fontWeight: 600, fontSize: 13, opacity: loading || (exportMode === 'sesi' && !filter.session_id) || (exportMode === 'bulan' && !filter.bulan) ? 0.5 : 1,
                        transition: 'opacity 0.15s', width: '100%'
                    }}>
                    {loading ? 'Mengexport...' : '⬇ Download Excel'}
                </button>

                <div style={{ marginTop: 16, padding: '10px 14px', background: '#f8fafc', borderRadius: 7, fontSize: 11, color: '#64748b', border: '1px solid #e2e8f0' }}>
                    File akan berisi kolom <strong>Tipe (Match/Beda)</strong>, <strong>Alasan Beda</strong>, dan <strong>Stand Koreksi</strong> dengan pewarnaan status otomatis.
                </div>
            </div>
        </div>
    )
}