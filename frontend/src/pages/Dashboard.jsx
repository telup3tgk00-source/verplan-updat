import { useEffect, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useAuthStore } from '../store/authStore'
import DashboardUID from './DashboardUID'

function StatCard({ label, value, color, subtext }) {
    return (
        <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: '20px 24px', border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
                {color && <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}80` }} />}
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#0f172a', letterSpacing: '-1px', lineHeight: 1.2 }}>{typeof value === 'number' ? value.toLocaleString() : value}</div>
            {subtext && <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 8, fontWeight: 500 }}>{subtext}</div>}
        </div>
    )
}

export default function Dashboard() {
    const { role } = useAuthStore()

    if (['uid', 'super_admin', 'up3'].includes(role)) {
        return <DashboardUID />
    }

    useEffect(() => { document.title = "Dashboard | METRIK" }, [])

    const [selectedBulan, setSelectedBulan] = useState('')

    const { data: sessions } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const uniqueBulan = useMemo(() => {
        if (!sessions) return []
        const bln = sessions.map(s => s.bulan_verifikasi).filter(Boolean)
        return [...new Set(bln)].sort((a, b) => b.localeCompare(a)) // terbaru di atas
    }, [sessions])

    useEffect(() => {
        if (uniqueBulan.length > 0 && !selectedBulan) {
            setSelectedBulan(uniqueBulan[0])
        }
    }, [uniqueBulan])

    const { data: stats, isLoading } = useQuery({
        queryKey: ['dashboard-stats', selectedBulan],
        queryFn: () => api.get(`/api/dashboard/stats${selectedBulan ? `?bulan=${selectedBulan}` : ''}`).then(r => r.data),
        refetchInterval: 10000,
    })

    const formatBulan = (val) => {
        if (!val || val.length !== 6) return val
        const y = val.substring(0, 4)
        const m = val.substring(4, 6)
        const months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        return `${months[parseInt(m) - 1] || m} ${y}`
    }

    if (isLoading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: '#94a3b8', fontSize: 13 }}>
            Memuat data...
        </div>
    )

    const totalDone = (stats?.verified_ok || 0) + (stats?.verified_reject || 0) + (stats?.need_investigation || 0)

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Dashboard</h1>
                    <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Pemantauan real-time verifikasi data meter PLN</p>
                </div>
                <div>
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

            {/* Stat Cards */}
            <div className="animate-slide-up grid-stats">
                <StatCard label="Total Data" value={stats?.total || 0} subtext={selectedBulan ? `Periode ${formatBulan(selectedBulan)}` : "Semua sesi aktif"} color="#3b82f6" />
                <StatCard label="Selesai" value={totalDone} color="#10b981" subtext={`${stats?.progress_pct || 0}% dari total`} />
                <StatCard label="Pending" value={stats?.pending || 0} color="#f59e0b" subtext="Menunggu verifikator" />
                <StatCard label="Anomali" value={stats?.anomaly || 0} color="#ef4444" subtext="Selisih > 500 KWH" />
            </div>

            {/* Charts */}
            <div className="animate-slide-up delay-100 grid-charts">
                {/* Bar Chart */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Progres Per Sesi</div>
                    <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 24 }}>5 sesi terakhir (persentase selesai)</div>
                    <div style={{ height: 240 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats?.chart_data} barCategoryGap="35%">
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                <XAxis dataKey="name" fontSize={12} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} dy={10} />
                                <YAxis fontSize={12} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} unit="%" domain={[0, 100]} dx={-10} />
                                <Tooltip
                                    contentStyle={{ borderRadius: 10, border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.1)', fontSize: 13, padding: '12px 16px', fontWeight: 500 }}
                                    cursor={{ fill: '#f1f5f9' }}
                                    formatter={(val, name, props) => [`${val}% (${props.payload.done?.toLocaleString() || 0} dari ${props.payload.total?.toLocaleString() || 0})`, 'Selesai']}
                                />
                                <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
                                    {stats?.chart_data?.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.pct > 80 ? '#10b981' : 'url(#colorPct)'} />
                                    ))}
                                </Bar>
                                <defs>
                                    <linearGradient id="colorPct" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={1}/>
                                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0.8}/>
                                    </linearGradient>
                                </defs>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Breakdown */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Distribusi Status</div>
                    <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 24 }}>Proporsi hasil verifikasi</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                        {[
                            { label: 'Setuju / OK', value: stats?.verified_ok, color: '#10b981' },
                            { label: 'Investigasi', value: stats?.need_investigation, color: '#f59e0b' },
                            { label: 'Belum Dikerjakan', value: stats?.pending, color: '#94a3b8' },
                        ].map(item => {
                            const pct = stats?.total ? ((item.value || 0) / stats.total * 100) : 0
                            return (
                                <div key={item.label}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8, color: '#334155', fontWeight: 500 }}>
                                        <span>{item.label}</span>
                                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{(item.value || 0).toLocaleString()}</span>
                                    </div>
                                    <div style={{ height: 8, background: '#f1f5f9', borderRadius: 4, overflow: 'hidden' }}>
                                        <div style={{ width: `${pct}%`, height: '100%', background: item.color, borderRadius: 4, transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)' }} />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </div>

            {/* Session table */}
            <div className="animate-slide-up delay-200 card-hover" style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid #f1f5f9', fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                    Aktivitas Sesi Terakhir
                </div>
                {!sessions?.length ? (
                    <div style={{ padding: 32, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Belum ada data upload.</div>
                ) : (
                    <div className="table-responsive">
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                                <tr style={{ background: '#f8fafc' }}>
                                    {['Sesi', 'Nama Batch', 'Waktu Upload', 'Total Record', 'Status'].map(h => (
                                        <th key={h} style={{ padding: '10px 20px', textAlign: 'left', color: '#64748b', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {sessions
                                    .filter(s => !selectedBulan || s.bulan_verifikasi === selectedBulan)
                                    .slice(0, 5)
                                    .map(s => {
                                        const localIndex = sessions.length - sessions.indexOf(s);
                                        return (
                                        <tr key={s.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '12px 20px', fontWeight: 600, color: '#0f172a' }}>#{localIndex}</td>
                                        <td style={{ padding: '12px 20px', color: '#0f172a', fontWeight: 500 }}>{s.batch_name || '—'}</td>
                                        <td style={{ padding: '12px 20px', color: '#64748b' }}>{new Date(s.created_at).toLocaleString('id-ID')}</td>
                                        <td style={{ padding: '12px 20px', color: '#374151' }}>{s.total_records?.toLocaleString() || '—'}</td>
                                        <td style={{ padding: '12px 20px' }}>
                                            <span style={{
                                                padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                                                background: s.status === 'done' ? '#f0fdf4' : s.status === 'processing' ? '#fffbeb' : '#fef2f2',
                                                color: s.status === 'done' ? '#16a34a' : s.status === 'processing' ? '#d97706' : '#dc2626',
                                                border: `1px solid ${s.status === 'done' ? '#bbf7d0' : s.status === 'processing' ? '#fde68a' : '#fecaca'}`
                                            }}>
                                                {s.status === 'done' ? 'Selesai' : s.status === 'processing' ? 'Diproses' : s.status}
                                            </span>
                                        </td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}