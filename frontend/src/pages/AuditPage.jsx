import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'

export default function AuditPage() {
    useEffect(() => { document.title = "Audit Trail | METRIK" }, [])
    
    const [page, setPage] = useState(0)
    const [selectedBulan, setSelectedBulan] = useState('')
    const [search, setSearch] = useState('')
    const [debouncedSearch, setDebouncedSearch] = useState('')
    const limit = 50

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedSearch(search), 500)
        return () => clearTimeout(timer)
    }, [search])

    // Reset page on filter change
    useEffect(() => { setPage(0) }, [selectedBulan, debouncedSearch])

    const { data: sessions } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const uniqueBulan = [...new Set((sessions || []).map(s => s.bulan_verifikasi).filter(Boolean))].sort((a, b) => b.localeCompare(a))

    const { data, isLoading } = useQuery({
        queryKey: ['audit-logs', page, selectedBulan, debouncedSearch],
        queryFn: () => api.get(`/api/audit?skip=${page * limit}&limit=${limit}${selectedBulan ? `&bulan=${selectedBulan}` : ''}${debouncedSearch ? `&search=${debouncedSearch}` : ''}`).then(r => r.data),
        keepPreviousData: true
    })

    const getStatusColor = (status) => {
        if (status === 'VERIFIED_OK') return { bg: '#f0fdf4', color: '#16a34a', border: '#bbf7d0', text: 'Setuju / OK' }
        if (status === 'VERIFIED_REJECT') return { bg: '#fef2f2', color: '#dc2626', border: '#fecaca', text: 'Tolak' }
        if (status === 'NEED_INVESTIGATION') return { bg: '#fffbeb', color: '#d97706', border: '#fde68a', text: 'Investigasi' }
        return { bg: '#f1f5f9', color: '#64748b', border: '#e2e8f0', text: status || '-' }
    }

    const formatBulan = (val) => {
        if (!val || val.length !== 6) return val
        const y = val.substring(0, 4)
        const m = val.substring(4, 6)
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        return `${months[parseInt(m) - 1] || m} ${y}`
    }

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.5px', margin: 0 }}>Audit Trail Keamanan</h1>
                    <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>Pelacakan jejak perubahan data verifikasi oleh operator (Akses Khusus Super Admin)</p>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                    <input 
                        type="text" 
                        placeholder="Cari ID Pelanggan..." 
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #cbd5e1', fontSize: 13, outline: 'none', width: 200 }}
                    />
                    <select
                        value={selectedBulan}
                        onChange={(e) => setSelectedBulan(e.target.value)}
                        style={{ padding: '8px 36px 8px 16px', borderRadius: 8, border: '1px solid #cbd5e1', fontSize: 13, fontWeight: 600, color: '#334155', background: '#fff', outline: 'none', cursor: 'pointer', appearance: 'none', backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2394a3b8%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center', backgroundSize: '10px auto' }}
                    >
                        <option value="">Semua Periode</option>
                        {uniqueBulan.map(b => (
                            <option key={b} value={b}>{formatBulan(b)}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="animate-slide-up" style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                {isLoading ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Memuat jejak audit...</div>
                ) : !data?.data?.length ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Belum ada log audit.</div>
                ) : (
                    <>
                        <div className="table-responsive">
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                <thead>
                                    <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Waktu</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Aktor (User)</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>ID Pelanggan</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Perubahan Status</th>
                                        <th style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Catatan Aktor</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.data.map((log) => {
                                        const oldStyle = getStatusColor(log.old_status)
                                        const newStyle = getStatusColor(log.new_status)
                                        return (
                                            <tr key={log.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                <td style={{ padding: '12px 16px', color: '#64748b', whiteSpace: 'nowrap' }}>
                                                    {new Date(log.created_at).toLocaleString('id-ID')}
                                                </td>
                                                <td style={{ padding: '12px 16px' }}>
                                                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{log.user_name}</div>
                                                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Unit: {log.user_kode || '-'}</div>
                                                </td>
                                                <td style={{ padding: '12px 16px', fontWeight: 600, color: '#3b82f6' }}>
                                                    {log.id_pelanggan}
                                                </td>
                                                <td style={{ padding: '12px 16px' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                        {log.old_status && (
                                                            <>
                                                                <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: oldStyle.bg, color: oldStyle.color, border: `1px solid ${oldStyle.border}` }}>
                                                                    {oldStyle.text}
                                                                </span>
                                                                <span style={{ color: '#cbd5e1' }}>→</span>
                                                            </>
                                                        )}
                                                        <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: newStyle.bg, color: newStyle.color, border: `1px solid ${newStyle.border}` }}>
                                                            {newStyle.text}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td style={{ padding: '12px 16px', color: '#334155', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={log.catatan}>
                                                    {log.catatan || '-'}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                        
                        {/* Pagination */}
                        <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', background: '#f8fafc' }}>
                            <div style={{ fontSize: 12, color: '#64748b' }}>
                                Menampilkan {data.skip + 1} - {Math.min(data.skip + limit, data.total)} dari {data.total} log
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button 
                                    onClick={() => setPage(p => Math.max(0, p - 1))} 
                                    disabled={page === 0}
                                    style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #cbd5e1', background: '#fff', cursor: page === 0 ? 'not-allowed' : 'pointer', opacity: page === 0 ? 0.5 : 1, fontSize: 12, fontWeight: 500 }}
                                >
                                    Sebelumnya
                                </button>
                                <button 
                                    onClick={() => setPage(p => p + 1)} 
                                    disabled={data.skip + limit >= data.total}
                                    style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #cbd5e1', background: '#fff', cursor: data.skip + limit >= data.total ? 'not-allowed' : 'pointer', opacity: data.skip + limit >= data.total ? 0.5 : 1, fontSize: 12, fontWeight: 500 }}
                                >
                                    Selanjutnya
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
