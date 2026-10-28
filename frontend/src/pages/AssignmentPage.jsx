import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/axios'
import { toast } from 'sonner'
import { useAuthStore } from '../store/authStore'

const inputStyle = { width: '100%', height: 36, padding: '0 11px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, outline: 'none', boxSizing: 'border-box', color: '#1e293b' }

export default function AssignmentPage() {
    useEffect(() => { document.title = "Pembagian Tugas | METRIK" }, [])

    const { role } = useAuthStore()
    const qc = useQueryClient()

    const [sessionId, setSessionId] = useState('')
    const [method, setMethod] = useState('auto')
    const [selectedOps, setSelectedOps] = useState([])
    const [rangeStart, setRangeStart] = useState('')
    const [rangeEnd, setRangeEnd] = useState('')
    const [prefix, setPrefix] = useState('')

    const { data: users = [] } = useQuery({
        queryKey: ['users'],
        queryFn: () => api.get('/api/users/').then(r => r.data),
    })

    const { data: sessions = [] } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
    })

    const { data: progress = [] } = useQuery({
        queryKey: ['assignment-progress', sessionId],
        queryFn: () => api.get(`/api/assignments/progress?session_id=${sessionId}`).then(r => r.data),
        enabled: !!sessionId,
        refetchInterval: 10000,
    })

    const assignMutation = useMutation({
        mutationFn: (data) => api.post('/api/assignments/', data),
        onSuccess: (res) => {
            toast.success(`${res.data.total_processed} record berhasil di-assign`)
            qc.invalidateQueries(['assignment-progress', sessionId])
            setRangeStart(''); setRangeEnd(''); setPrefix('')
        },
        onError: (err) => toast.error(err.response?.data?.detail || 'Gagal membagi tugas'),
    })

    const verifikators = users.filter(u => u.role === 'verifikator')

    const handleAssign = () => {
        if (!sessionId) return toast.error('Pilih sesi upload terlebih dahulu')
        if (selectedOps.length === 0) return toast.error('Pilih minimal 1 verifikator')
        assignMutation.mutate({
            session_id: parseInt(sessionId),
            method,
            operator_ids: selectedOps.map(id => parseInt(id)),
            range_start: method === 'range' ? rangeStart : null,
            range_end: method === 'range' ? rangeEnd : null,
            prefix: method === 'prefix' ? prefix : null
        })
    }

    const toggleOp = (id) => setSelectedOps(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

    if (!['super_admin', 'ulp'].includes(role)) return <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Akses ditolak.</div>

    const methods = [
        { key: 'auto', label: 'Bagi Rata (Auto Split)', desc: 'Bagi rata semua data ke verifikator yang dipilih' },
        { key: 'range', label: 'Range ID', desc: 'Berdasarkan rentang ID Pelanggan' },
        { key: 'prefix', label: 'Prefix ID', desc: 'Berdasarkan kode awalan' },
    ]

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Pembagian Tugas</h1>
                <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Bagi data <strong style={{ color: '#dc2626' }}>BEDA</strong> ke petugas untuk dikerjakan manual</p>
            </div>

            <div className="grid-assignment">
                {/* Config panel */}
                <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: 24 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 20 }}>Konfigurasi Pembagian</div>

                    {/* Step 1: Session */}
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: 8 }}>1 — Pilih Sesi Upload</label>
                        <select value={sessionId} onChange={e => setSessionId(e.target.value)} style={{ ...inputStyle }}>
                            <option value="">Pilih sesi...</option>
                            {sessions.filter(s => s.status === 'done').map(s => (
                                <option key={s.id} value={s.id}>{s.batch_name ? s.batch_name : `Sesi #${s.id}`} — {s.file_beda_name || s.file_match_name} ({s.total_beda?.toLocaleString() ?? s.total_records?.toLocaleString() ?? 0} data beda)</option>
                            ))}
                        </select>
                    </div>

                    {/* Step 2: Method */}
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: 8 }}>2 — Metode Pembagian</label>
                        <div style={{ display: 'flex', gap: 8 }}>
                            {methods.map(m => (
                                <button key={m.key} onClick={() => setMethod(m.key)}
                                    style={{
                                        flex: 1, padding: '10px 8px', borderRadius: 7,
                                        border: `1.5px solid ${method === m.key ? '#3b82f6' : '#e2e8f0'}`,
                                        background: method === m.key ? '#eff6ff' : '#fff',
                                        color: method === m.key ? '#1d4ed8' : '#64748b',
                                        fontSize: 11, fontWeight: method === m.key ? 600 : 400,
                                        cursor: 'pointer', textAlign: 'center', transition: 'all 0.12s'
                                    }}>
                                    <div style={{ fontWeight: 600, marginBottom: 2 }}>{m.label}</div>
                                    <div style={{ fontSize: 10, opacity: 0.7 }}>{m.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Conditional inputs */}
                    {method === 'range' && (
                        <div className="grid-upload" style={{ marginBottom: 20 }}>
                            <div>
                                <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5 }}>Dari ID</label>
                                <input value={rangeStart} onChange={e => setRangeStart(e.target.value)} placeholder="171000" style={inputStyle} />
                            </div>
                            <div>
                                <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5 }}>Sampai ID</label>
                                <input value={rangeEnd} onChange={e => setRangeEnd(e.target.value)} placeholder="171999" style={inputStyle} />
                            </div>
                        </div>
                    )}

                    {method === 'prefix' && (
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 5 }}>Prefix ID (3–5 digit awal)</label>
                            <input value={prefix} onChange={e => setPrefix(e.target.value)} placeholder="Contoh: 171" style={inputStyle} />
                        </div>
                    )}

                    {/* Step 3: Select operators */}
                    <div style={{ marginBottom: 24 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: 8 }}>
                            3 — Pilih Verifikator <span style={{ color: '#3b82f6' }}>({selectedOps.length} dipilih)</span>
                        </label>
                        {verifikators.length === 0 ? (
                            <div style={{ padding: 16, background: '#f8fafc', borderRadius: 7, fontSize: 12, color: '#94a3b8', border: '1px solid #e2e8f0' }}>Belum ada verifikator. Tambahkan di menu Kelola Akun.</div>
                        ) : (
                            <div className="grid-upload" style={{ maxHeight: 180, overflowY: 'auto', gap: 6 }}>
                                {verifikators.map(u => (
                                    <div key={u.id} onClick={() => toggleOp(u.id)}
                                        style={{
                                            padding: '8px 12px', borderRadius: 6, fontSize: 12,
                                            border: `1.5px solid ${selectedOps.includes(u.id) ? '#3b82f6' : '#e2e8f0'}`,
                                            background: selectedOps.includes(u.id) ? '#eff6ff' : '#fff',
                                            color: selectedOps.includes(u.id) ? '#1d4ed8' : '#374151',
                                            cursor: 'pointer', fontWeight: selectedOps.includes(u.id) ? 600 : 400,
                                            transition: 'all 0.1s', userSelect: 'none'
                                        }}>
                                        {u.full_name}
                                        {u.unit_penugasan && (
                                            <span style={{ marginLeft: 6, fontSize: 10, padding: '2px 6px', background: selectedOps.includes(u.id) ? '#dbeafe' : '#f1f5f9', color: selectedOps.includes(u.id) ? '#1e40af' : '#64748b', borderRadius: 4, fontFamily: 'monospace' }}>
                                                {u.unit_penugasan}
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleAssign}
                        disabled={assignMutation.isPending || !sessionId || selectedOps.length === 0}
                        style={{
                            width: '100%', height: 40, background: '#0f172a', color: '#fff',
                            border: 'none', borderRadius: 7, fontWeight: 600, fontSize: 13,
                            cursor: 'pointer', opacity: (!sessionId || selectedOps.length === 0 || assignMutation.isPending) ? 0.5 : 1,
                            transition: 'opacity 0.15s'
                        }}>
                        {assignMutation.isPending ? 'Memproses...' : 'Jalankan Pembagian'}
                    </button>
                </div>

                {/* Progress panel */}
                <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                    <div style={{ padding: '14px 20px', borderBottom: '1px solid #f1f5f9', fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                        Progres Sesi {sessionId ? `#${sessionId}` : ''}
                    </div>
                    {!sessionId ? (
                        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Pilih sesi untuk melihat progres</div>
                    ) : progress.length === 0 ? (
                        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Belum ada tugas di sesi ini</div>
                    ) : (
                        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                            {progress.map(p => {
                                const name = verifikators.find(u => u.id === p.operator_id)?.full_name || `User #${p.operator_id}`
                                return (
                                    <div key={p.operator_id}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                            <span style={{ fontSize: 12, fontWeight: 500, color: '#1e293b' }}>{name}</span>
                                            <span style={{ fontSize: 11, color: '#64748b' }}>{p.selesai} / {p.total_assigned} ({p.pct}%)</span>
                                        </div>
                                        <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
                                            <div style={{ width: `${p.pct}%`, height: '100%', background: p.pct >= 100 ? '#16a34a' : '#3b82f6', borderRadius: 3, transition: 'width 0.4s ease' }} />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
