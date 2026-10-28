import { useEffect, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/axios'
import { 
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, 
    PieChart, Pie, Cell, Legend, BarChart, Bar 
} from 'recharts'
import { useAuthStore } from '../store/authStore'

function StatCard({ label, value, color, subtext, trend }) {
    return (
        <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: '20px 24px', border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
                {color && <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}80` }} />}
            </div>
            <div>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#0f172a', letterSpacing: '-1px', lineHeight: 1.2 }}>{typeof value === 'number' ? value.toLocaleString() : value}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                    {subtext && <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500 }}>{subtext}</div>}
                    {trend && (
                        <div style={{ fontSize: 12, fontWeight: 600, color: trend.isPositive ? '#10b981' : '#ef4444', background: trend.isPositive ? '#ecfdf5' : '#fef2f2', padding: '2px 8px', borderRadius: 12 }}>
                            {trend.isPositive ? '↑' : '↓'} {trend.value}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

export default function DashboardUID() {
    const { role } = useAuthStore()

    useEffect(() => { 
        document.title = role === 'super_admin' ? "Dashboard Nasional | METRIK" : role === 'up3' ? "Dashboard UP3 | METRIK" : "Dashboard UID | METRIK" 
    }, [role])

    // Default ke bulan saat ini langsung — tanpa menunggu sessions API
    // agar query pertama SELALU punya filter bulan (tidak scan 1.6M rows)
    const getCurrentBulan = () => {
        const now = new Date()
        const y = now.getFullYear()
        const m = String(now.getMonth() + 1).padStart(2, '0')
        return `${y}${m}`
    }
    const [selectedBulan, setSelectedBulan] = useState(getCurrentBulan)

    const { data: sessions } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const uniqueBulan = useMemo(() => {
        if (!sessions) return []
        const bln = sessions.map(s => s.bulan_verifikasi).filter(Boolean)
        return [...new Set(bln)].sort((a, b) => b.localeCompare(a)) 
    }, [sessions])

    // Sinkronkan ke bulan terbaru dari data (jika bulan aktif tidak ada di sesi, pakai yang terbaru)
    useEffect(() => {
        if (uniqueBulan.length > 0 && !uniqueBulan.includes(selectedBulan)) {
            setSelectedBulan(uniqueBulan[0])
        }
    }, [uniqueBulan])

    // Top Level Stats
    const { data: stats, isLoading: isStatsLoading } = useQuery({
        queryKey: ['dashboard-stats', selectedBulan],
        queryFn: () => api.get(`/api/dashboard/stats${selectedBulan ? `?bulan=${selectedBulan}` : ''}`).then(r => r.data),
        enabled: !!selectedBulan,   // Jangan fetch sebelum bulan dipilih
        refetchInterval: 300000,    // 5 menit — backend sudah cache 2 menit, refresh terlalu sering buang-buang DB
        staleTime: 60000,           // Anggap data segar selama 1 menit
    })

    // UID Specific Analytics
    const { data: uidData, isLoading: isUidLoading } = useQuery({
        queryKey: ['dashboard-uid', selectedBulan],
        queryFn: () => api.get(`/api/dashboard/uid${selectedBulan ? `?bulan=${selectedBulan}` : ''}`).then(r => r.data),
        enabled: !!selectedBulan,   // Jangan fetch sebelum bulan dipilih
        refetchInterval: 300000,    // 5 menit
        staleTime: 60000,
    })

    const formatBulan = (val) => {
        if (!val || val.length !== 6) return val
        const y = val.substring(0, 4)
        const m = val.substring(4, 6)
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        return `${months[parseInt(m) - 1] || m} ${y}`
    }

    if (isStatsLoading || isUidLoading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: '#94a3b8', fontSize: 13 }}>
            Memuat analitik UID...
        </div>
    )

    const totalDone = (stats?.verified_ok || 0) + (stats?.verified_reject || 0) + (stats?.need_investigation || 0)
    const pctSelesai = stats?.total ? ((totalDone / stats.total) * 100).toFixed(1) : 0

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.5px', margin: 0 }}>
                        {role === 'super_admin' ? 'Dashboard Nasional PLN' : role === 'up3' ? 'Dashboard UP3' : 'Dashboard Unit Induk Distribusi'}
                    </h1>
                    <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                        {role === 'super_admin' ? 'Pantauan performa verifikasi seluruh UID se-Indonesia' : role === 'up3' ? 'Pantauan performa verifikasi seluruh ULP di bawah UP3' : 'Pantauan performa verifikasi seluruh UP3 dan ULP'}
                    </p>
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

            {/* Stat Cards - Top Level */}
            <div className="animate-slide-up" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20, marginBottom: 24 }}>
                <StatCard label="Total Volume" value={stats?.total || 0} subtext="Target Data KWH" color="#3b82f6" />
                <StatCard label="Pencapaian" value={totalDone} subtext={`${pctSelesai}% dari Total Volume`} color="#10b981" trend={{ isPositive: pctSelesai > 50, value: `${pctSelesai}%` }} />
                <StatCard label="Pending SLA" value={stats?.pending || 0} subtext="Menunggu Eksekusi ULP" color="#f59e0b" />
                <StatCard label="Data Anomali" value={stats?.anomaly || 0} subtext="Butuh Investigasi" color="#ef4444" trend={{ isPositive: false, value: 'Warning' }} />
            </div>

            {/* Middle Section: Leaderboard & Trend */}
            <div className="animate-slide-up delay-100" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 20, marginBottom: 24 }}>
                
                {/* UP3/ULP Leaderboard */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
                        {role === 'super_admin' ? 'Peringkat Kinerja UID' : role === 'up3' ? 'Peringkat Kinerja ULP' : 'Peringkat Kinerja UP3'}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>Berdasarkan persentase penyelesaian</div>
                    
                    <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4, display: 'flex', flexDirection: 'column', gap: 16 }}>
                        {uidData?.leaderboard?.map((unit, index) => (
                            <div key={unit.kode_unit}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <div style={{ fontSize: 11, fontWeight: 700, color: index === 0 ? '#10b981' : '#94a3b8', background: index === 0 ? '#ecfdf5' : '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>#{index + 1}</div>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>
                                            {unit.nama_unit || (role === 'super_admin' ? `UID ${unit.kode_unit}` : role === 'up3' ? `ULP ${unit.kode_unit}` : `UP3 ${unit.kode_unit}`)}
                                        </div>
                                    </div>
                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>{unit.progress_pct}%</div>
                                </div>
                                <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
                                    <div style={{ width: `${unit.progress_pct}%`, height: '100%', background: unit.progress_pct > 80 ? '#10b981' : unit.progress_pct > 40 ? '#3b82f6' : '#f59e0b', borderRadius: 3, transition: 'width 1s ease-in-out' }} />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 11, color: '#94a3b8' }}>
                                    <span>Selesai: {unit.done.toLocaleString()}</span>
                                    <span>Sisa: {(unit.total - unit.done).toLocaleString()}</span>
                                </div>
                            </div>
                        ))}
                        {(!uidData?.leaderboard || uidData.leaderboard.length === 0) && (
                            <div style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center', padding: '20px 0' }}>
                                Belum ada data {role === 'super_admin' ? 'UID' : role === 'up3' ? 'ULP' : 'UP3'}.
                            </div>
                        )}
                    </div>
                </div>

                {/* Daily Trend Chart */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Tren Penyelesaian (7 Hari Terakhir)</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>Throughput verifikasi harian seluruh wilayah</div>
                    
                    <div style={{ height: 260 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={uidData?.daily_trend}>
                                <defs>
                                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="date" fontSize={11} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} dy={10} 
                                    tickFormatter={(val) => {
                                        const d = new Date(val);
                                        return `${d.getDate()} ${['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'][d.getMonth()]}`;
                                    }}
                                />
                                <YAxis fontSize={11} axisLine={false} tickLine={false} tick={{ fill: '#64748b' }} dx={-10} />
                                <RechartsTooltip 
                                    contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', fontSize: 12 }}
                                    formatter={(value) => [value.toLocaleString(), 'Diselesaikan']}
                                    labelFormatter={(label) => `Tanggal: ${label}`}
                                />
                                <Area type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorCount)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Bottom Section: Anomaly Breakdown & Bottlenecks */}
            <div className="animate-slide-up delay-200" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                
                {/* Anomaly Breakdown */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Sebaran Tipe Anomali</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>Proporsi alasan anomali yang ditemukan</div>
                    
                    <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {uidData?.anomaly_breakdown?.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={uidData.anomaly_breakdown}
                                        innerRadius={60}
                                        outerRadius={80}
                                        paddingAngle={5}
                                        dataKey="count"
                                        nameKey="reason"
                                    >
                                        {uidData.anomaly_breakdown.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <RechartsTooltip 
                                        contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', fontSize: 12 }}
                                        formatter={(val) => [val.toLocaleString(), 'Jumlah']}
                                    />
                                    <Legend verticalAlign="middle" align="right" layout="vertical" iconType="circle" wrapperStyle={{ fontSize: 12, color: '#475569' }} />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ fontSize: 12, color: '#94a3b8' }}>Tidak ada data anomali.</div>
                        )}
                    </div>
                </div>

                {/* Bottlenecks Warning */}
                <div className="card-hover" style={{ background: '#fff', borderRadius: 12, padding: 24, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                        <div>
                            <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Peringatan Bottleneck / Tertunda</div>
                            <div style={{ fontSize: 12, color: '#64748b' }}>Sesi dengan antrean pending terlama</div>
                        </div>
                        <div style={{ background: '#fef2f2', color: '#ef4444', padding: '6px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#ef4444', animation: 'pulse 2s infinite' }} />
                            Perlu Perhatian
                        </div>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {uidData?.bottlenecks?.length > 0 ? (
                            uidData.bottlenecks.map((b, idx) => (
                                <div key={idx} style={{ padding: '12px 16px', border: '1px solid #f1f5f9', borderRadius: 8, background: '#fafaf9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>{b.batch_name || 'Batch Tanpa Nama'}</div>
                                        <div style={{ fontSize: 11, color: '#64748b' }}>
                                            <span style={{ color: '#ef4444', fontWeight: 600 }}>{b.pending_count.toLocaleString()} data pending</span> 
                                            <span style={{ margin: '0 6px' }}>•</span>
                                            Tertunda {b.days_pending} hari
                                        </div>
                                    </div>
                                    <div>
                                        <span style={{ padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, 
                                            background: b.status === 'Kritis' ? '#fef2f2' : '#fffbeb', 
                                            color: b.status === 'Kritis' ? '#ef4444' : '#d97706',
                                            border: `1px solid ${b.status === 'Kritis' ? '#fecaca' : '#fde68a'}`
                                        }}>
                                            {b.status}
                                        </span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div style={{ textAlign: 'center', padding: '30px 0', color: '#10b981', fontSize: 13, fontWeight: 500, background: '#f0fdf4', borderRadius: 8, border: '1px dashed #a7f3d0' }}>
                                Luar biasa! Tidak ada data yang menumpuk atau tertunda.
                            </div>
                        )}
                    </div>
                </div>

            </div>
            <style>{`
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                    70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
                }
            `}</style>
        </div>
    )
}
