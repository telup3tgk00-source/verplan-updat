import React, { useEffect, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'
import { useAuthStore } from '../store/authStore'

export default function ProgressPage() {
    useEffect(() => { document.title = "Progres Operator | METRIK" }, [])

    const { role } = useAuthStore()
    const [selectedBulan, setSelectedBulan] = useState('')

    const { data: sessions } = useQuery({
        queryKey: ['sessions-for-filter'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const uniqueBulan = useMemo(() => {
        if (!sessions) return []
        const bln = sessions.map(s => s.bulan_verifikasi).filter(Boolean)
        return [...new Set(bln)].sort((a, b) => b.localeCompare(a))
    }, [sessions])

    useEffect(() => {
        if (uniqueBulan.length > 0 && !selectedBulan) {
            setSelectedBulan(uniqueBulan[0])
        }
    }, [uniqueBulan])

    const { data: stats, isLoading } = useQuery({
        queryKey: ['progress-detail', selectedBulan],
        queryFn: () => api.get(`/api/dashboard/stats${selectedBulan ? `?bulan=${selectedBulan}` : ''}`).then(r => r.data),
        refetchInterval: 15000,
    })

    const { data: ulpProgress = [] } = useQuery({
        queryKey: ['progress-ulp', selectedBulan],
        queryFn: () => api.get(`/api/dashboard/progress-ulp${selectedBulan ? `?bulan=${selectedBulan}` : ''}`).then(r => r.data),
        refetchInterval: 15000,
    })

    const isUID = role === 'uid' || role === 'super_admin';

    const groupedProgress = useMemo(() => {
        if (!Array.isArray(ulpProgress)) return [];
        if (!isUID) return ulpProgress;

        const groups = {};
        ulpProgress.forEach(row => {
            if (!row || !row.kode_unit) return;
            
            let up3 = "";
            const kodeStr = String(row.kode_unit);
            if (kodeStr.includes('-')) {
                const parts = kodeStr.split('-');
                up3 = parts.length >= 2 ? `${parts[0]}-${parts[1]}` : parts[0];
            } else {
                up3 = kodeStr.substring(0, 3);
            }

            if (!groups[up3]) {
                groups[up3] = {
                    up3_code: up3,
                    total: 0, verified_ok: 0, need_investigation: 0, pending: 0,
                    children: []
                };
            }
            groups[up3].total += Number(row.total || 0);
            groups[up3].verified_ok += Number(row.verified_ok || 0);
            groups[up3].need_investigation += Number(row.need_investigation || 0);
            groups[up3].pending += Number(row.pending || 0);
            groups[up3].children.push(row);
        });

        return Object.values(groups).map(g => {
            g.progress_pct = g.total > 0 ? Math.round((g.verified_ok + g.need_investigation) / g.total * 1000) / 10 : 0;
            return g;
        });
    }, [ulpProgress, isUID]);

    const getUp3Name = (code) => {
        const map = { '171': 'TANJUNG KARANG', '172': 'METRO', '173': 'KOTABUMI', '174': 'PRINGSEWU' };
        return map[code] || code;
    };

    if (isLoading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: '#94a3b8', fontSize: 13 }}>
            Memuat data...
        </div>
    )

    const total = stats?.total || 1
    const bars = [
        { label: 'Setuju', val: stats?.verified_ok || 0, color: '#16a34a' },
        { label: 'Investigasi', val: stats?.need_investigation || 0, color: '#d97706' },
        { label: 'Pending', val: stats?.pending || 0, color: '#e2e8f0' },
    ]



    const formatBulan = (val) => {
        if (!val || val.length !== 6) return val
        const y = val.substring(0, 4)
        const m = val.substring(4, 6)
        const months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        return `${months[parseInt(m) - 1] || m} ${y}`
    }

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Monitoring Progres</h1>
                    <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Data diperbarui otomatis setiap 15 detik</p>
                </div>
                <div>
                    <select
                        value={selectedBulan}
                        onChange={e => setSelectedBulan(e.target.value)}
                        style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1', fontSize: 13, background: '#fff', color: '#0f172a', fontWeight: 500, outline: 'none' }}
                    >
                        <option value="">Semua Bulan</option>
                        {uniqueBulan.map(b => (
                            <option key={b} value={b}>{formatBulan(b)}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Overall progress */}
            <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: 24, marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#0f172a' }}>Progres Keseluruhan</span>
                    <span style={{ fontWeight: 700, color: '#16a34a', fontSize: 22 }}>{stats?.progress_pct || 0}%</span>
                </div>

                {/* Stacked bar */}
                <div style={{ height: 10, background: '#f1f5f9', borderRadius: 5, overflow: 'hidden', display: 'flex', marginBottom: 16 }}>
                    {bars.filter(b => b.val > 0).map(b => (
                        <div
                            key={b.label}
                            style={{ width: `${(b.val / total) * 100}%`, background: b.color, transition: 'width 0.5s ease' }}
                            title={`${b.label}: ${b.val.toLocaleString()}`}
                        />
                    ))}
                </div>

                {/* Legend */}
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                    {bars.map(b => (
                        <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: b.color, border: b.color === '#e2e8f0' ? '1px solid #cbd5e1' : 'none' }} />
                            <span style={{ color: '#64748b' }}>{b.label}</span>
                            <strong style={{ color: '#0f172a' }}>{b.val.toLocaleString()}</strong>
                            <span style={{ color: '#94a3b8' }}>({Math.round((b.val / total) * 100)}%)</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Summary cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
                {bars.map(b => (
                    <div key={b.label} style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: '18px 20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 2, background: b.color, border: b.color === '#e2e8f0' ? '1px solid #cbd5e1' : 'none', flexShrink: 0 }} />
                            <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{b.label}</span>
                        </div>
                        <div style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.5px' }}>{b.val.toLocaleString()}</div>
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{Math.round((b.val / total) * 100)}% dari total</div>
                    </div>
                ))}
            </div>
            {/* Table Progress Per ULP */}
            {Array.isArray(ulpProgress) && ulpProgress.length > 0 && (
                <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: 24, marginTop: 16 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a', marginBottom: 14 }}>Progres Per ULP</div>
                    <div className="table-responsive">
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                                <tr style={{ background: '#f8fafc' }}>
                                    <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: 500 }}>Unit / Nama ULP</th>
                                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: 500 }}>Total Data</th>
                                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: 500 }}>Selesai (OK)</th>
                                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: 500 }}>Investigasi</th>
                                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: 500 }}>Pending</th>
                                    <th style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b', fontWeight: 500 }}>Progres %</th>
                                </tr>
                            </thead>
                            <tbody>
                                {!isUID && ulpProgress.map((row, idx) => (
                                    <tr key={row?.kode_unit || idx} style={{ borderTop: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '10px 16px', color: '#0f172a', fontWeight: 500 }}>
                                            {row?.nama_ulp} <span style={{ color: '#94a3b8', fontSize: 11 }}>({row?.kode_unit})</span>
                                        </td>
                                        <td style={{ padding: '10px 16px', textAlign: 'right', color: '#0f172a' }}>{Number(row?.total || 0).toLocaleString()}</td>
                                        <td style={{ padding: '10px 16px', textAlign: 'right', color: '#16a34a', fontWeight: row?.verified_ok > 0 ? 600 : 400 }}>{Number(row?.verified_ok || 0).toLocaleString()}</td>
                                        <td style={{ padding: '10px 16px', textAlign: 'right', color: '#d97706', fontWeight: row?.need_investigation > 0 ? 600 : 400 }}>{Number(row?.need_investigation || 0).toLocaleString()}</td>
                                        <td style={{ padding: '10px 16px', textAlign: 'right', color: '#64748b' }}>{Number(row?.pending || 0).toLocaleString()}</td>
                                        <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                            <span style={{ 
                                                padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                                                background: Number(row?.progress_pct || 0) >= 100 ? '#f0fdf4' : Number(row?.progress_pct || 0) > 0 ? '#eff6ff' : '#f1f5f9',
                                                color: Number(row?.progress_pct || 0) >= 100 ? '#16a34a' : Number(row?.progress_pct || 0) > 0 ? '#2563eb' : '#94a3b8'
                                            }}>
                                                {Number(row?.progress_pct || 0)}%
                                            </span>
                                        </td>
                                    </tr>
                                ))}

                                {isUID && groupedProgress.map(g => (
                                    <React.Fragment key={g.up3_code}>
                                        {/* Header Row for UP3 */}
                                        <tr style={{ background: '#f8fafc', borderTop: '2px solid #cbd5e1', borderBottom: '1px solid #e2e8f0' }}>
                                            <td style={{ padding: '12px 16px', fontWeight: 700, color: '#0f172a' }} colSpan={1}>
                                                UP3 {getUp3Name(g.up3_code)} <span style={{ color: '#64748b', fontSize: 11, fontWeight: 500 }}>({g.up3_code})</span>
                                            </td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: '#0f172a' }}>{g.total.toLocaleString()}</td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: '#16a34a' }}>{g.verified_ok.toLocaleString()}</td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: '#d97706' }}>{g.need_investigation.toLocaleString()}</td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: '#64748b' }}>{g.pending.toLocaleString()}</td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                                                <span style={{ 
                                                    padding: '4px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                                                    background: g.progress_pct >= 100 ? '#16a34a' : g.progress_pct > 0 ? '#2563eb' : '#64748b',
                                                    color: '#fff'
                                                }}>
                                                    {g.progress_pct}%
                                                </span>
                                            </td>
                                        </tr>
                                        {/* Children Rows for ULP */}
                                        {g.children.map((row, idx) => (
                                            <tr key={row.kode_unit || idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                <td style={{ padding: '10px 16px 10px 32px', color: '#475569', fontWeight: 500 }}>
                                                    ↳ {row.nama_ulp} <span style={{ color: '#94a3b8', fontSize: 11 }}>({row.kode_unit})</span>
                                                </td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right', color: '#475569' }}>{Number(row.total || 0).toLocaleString()}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right', color: '#16a34a' }}>{Number(row.verified_ok || 0).toLocaleString()}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right', color: '#d97706' }}>{Number(row.need_investigation || 0).toLocaleString()}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right', color: '#94a3b8' }}>{Number(row.pending || 0).toLocaleString()}</td>
                                                <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                                    <span style={{ 
                                                        padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                                                        background: Number(row.progress_pct || 0) >= 100 ? '#f0fdf4' : Number(row.progress_pct || 0) > 0 ? '#eff6ff' : '#f1f5f9',
                                                        color: Number(row.progress_pct || 0) >= 100 ? '#16a34a' : Number(row.progress_pct || 0) > 0 ? '#2563eb' : '#94a3b8'
                                                    }}>
                                                        {Number(row.progress_pct || 0)}%
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </React.Fragment>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}