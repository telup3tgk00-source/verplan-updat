import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/axios'
import { toast } from 'sonner'
import { useAuthStore } from '../store/authStore'

const inputStyle = { width: '100%', height: 36, padding: '0 11px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, outline: 'none', boxSizing: 'border-box', color: '#1e293b' }

export default function UploadPage() {
    useEffect(() => { document.title = "Upload | METRIK" }, [])

    const { role } = useAuthStore()
    const qc = useQueryClient()
    const [fileMatch, setFileMatch] = useState(null)
    const [fileBeda, setFileBeda] = useState(null)
    const [batchName, setBatchName] = useState('')
    const [dialog, setDialog] = useState(null)

    // Generate daftar bulan: bulan ini + 5 bulan ke belakang
    const bulanOptions = (() => {
        const list = []
        const now = new Date()
        for (let i = 0; i < 6; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
            const y = d.getFullYear()
            const m = String(d.getMonth() + 1).padStart(2, '0')
            const label = d.toLocaleString('id-ID', { month: 'long', year: 'numeric' })
            list.push({ value: `${y}${m}`, label })
        }
        return list
    })()

    // Default: bulan berjalan
    const [bulanVerifikasi, setBulanVerifikasi] = useState(bulanOptions[0].value)

    const refMatch = useRef()
    const refBeda = useRef()

    const { data: sessions = [] } = useQuery({
        queryKey: ['sessions'],
        queryFn: () => api.get('/api/upload/sessions').then(r => r.data),
        refetchInterval: 5000,
    })

    const upload = useMutation({
        mutationFn: () => {
            const fd = new FormData()
            fd.append('file_match', fileMatch)
            fd.append('file_beda', fileBeda)
            if (batchName) fd.append('batch_name', batchName)
            fd.append('bulan_verifikasi', bulanVerifikasi)
            return api.post('/api/upload/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
        },
        onSuccess: () => {
            toast.success('File berhasil diupload, sedang diproses...')
            qc.invalidateQueries(['sessions'])
            qc.invalidateQueries(['dashboard-stats'])
            setFileMatch(null); setFileBeda(null); setBatchName('')
            if (refMatch.current) refMatch.current.value = ''
            if (refBeda.current) refBeda.current.value = ''
        },
        onError: (err) => toast.error(err?.response?.data?.detail || 'Gagal upload file'),
    })

    const deleteSession = useMutation({
        mutationFn: (id) => api.delete(`/api/upload/sessions/${id}`),
        onSuccess: () => { toast.success('Sesi dihapus'); qc.invalidateQueries(['sessions']); qc.invalidateQueries(['dashboard-stats']) },
        onError: () => toast.error('Gagal hapus sesi'),
    })

    if (!['super_admin', 'up3'].includes(role)) return <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Akses ditolak.</div>

    const canUpload = fileMatch && fileBeda && !upload.isPending

    const slots = [
        {
            label: 'File MATCH',
            desc: 'Data AI = Biller (langsung SESUAI)',
            ref: refMatch,
            set: setFileMatch,
            val: fileMatch,
            color: { border: '#86efac', bg: '#f0fdf4', icon: '#16a34a', iconBg: '#dcfce7' },
        },
        {
            label: 'File BEDA',
            desc: 'Data AI ≠ Biller (perlu dikerjakan)',
            ref: refBeda,
            set: setFileBeda,
            val: fileBeda,
            color: { border: '#fca5a5', bg: '#fff5f5', icon: '#dc2626', iconBg: '#fee2e2' },
        },
    ]

    return (
        <div style={{ fontFamily: "'Inter', -apple-system, sans-serif" }}>
            {upload.isPending && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(255,255,255,0.8)', zIndex: 99999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(3px)' }}>
                    <div style={{ width: 40, height: 40, border: '4px solid #cbd5e1', borderTopColor: '#0f172a', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                    <div style={{ marginTop: 20, fontSize: 16, fontWeight: 600, color: '#0f172a' }}>Sedang Mengupload & Memproses Data...</div>
                    <div style={{ marginTop: 8, fontSize: 13, color: '#64748b' }}>Mohon JANGAN tutup atau pindah halaman ini.</div>
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
            )}
            {dialog && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ background: '#fff', borderRadius: 10, width: 400, maxWidth: '90%', padding: 24, boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
                        <h3 style={{ margin: '0 0 12px 0', fontSize: 16, color: '#0f172a' }}>{dialog.title}</h3>
                        <p style={{ margin: '0 0 20px 0', fontSize: 13, color: '#475569', lineHeight: 1.5 }}>{dialog.message}</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                            <button onClick={() => setDialog(null)} style={{ padding: '8px 16px', background: '#f1f5f9', color: '#475569', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>Batal</button>
                            <button onClick={() => { dialog.onConfirm(); setDialog(null) }} style={{ padding: '8px 16px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
                                Konfirmasi
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.4px', margin: 0 }}>Upload Match & Beda</h1>
                <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Upload hasil dari Web 1: File MATCH (sudah sesuai) dan File BEDA (perlu dikerjakan petugas)</p>
            </div>

            {/* Info banner */}
            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: '10px 16px', marginBottom: 20, fontSize: 12, color: '#1d4ed8' }}>
                <strong>ℹ️ Info:</strong> File MATCH → langsung dianggap <strong>SESUAI</strong>, tidak perlu dikerjakan petugas.
                File BEDA → akan dibagi ke petugas untuk dikerjakan secara manual.
            </div>

            {/* Upload card */}
            <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', padding: 24, marginBottom: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', marginBottom: 16 }}>Upload File Baru</div>
                
                <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: 12, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 6 }}>
                        Nama Batch <span style={{ color: '#94a3b8', fontWeight: 400 }}>(Opsional - untuk membedakan sesi)</span>
                    </label>
                    <input 
                        type="text" 
                        value={batchName} 
                        onChange={e => setBatchName(e.target.value)} 
                        placeholder="Contoh: Data Bulan Mei Area 1" 
                        style={inputStyle} 
                    />
                </div>

                {/* Bulan Verifikasi */}
                <div style={{ marginBottom: 16 }}>
                    <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                        Bulan Verifikasi ACMT{' '}
                        <span style={{ color: '#ef4444' }}>*</span>
                        <span style={{ color: '#94a3b8', fontWeight: 400, marginLeft: 4 }}>
                            — foto meter dari ACMT akan dikunci ke bulan ini
                        </span>
                    </label>
                    <select
                        value={bulanVerifikasi}
                        onChange={e => setBulanVerifikasi(e.target.value)}
                        style={{ ...inputStyle, paddingLeft: 10, cursor: 'pointer' }}
                    >
                        {bulanOptions.map(opt => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label} ({opt.value})
                            </option>
                        ))}
                    </select>
                    <div style={{ marginTop: 5, fontSize: 11, color: '#0284c7', background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 5, padding: '5px 10px' }}>
                        ℹ️ Pilih bulan sesuai periode data yang diverifikasi, bukan bulan upload. Ini mengunci referensi foto ACMT untuk seluruh batch.
                    </div>
                </div>

                <div className="grid-upload">
                    {slots.map(({ label, desc, ref, set, val, color }) => (
                        <div key={label}
                            onClick={() => ref.current.click()}
                            style={{
                                border: `1.5px dashed ${val ? color.border : '#cbd5e1'}`,
                                borderRadius: 8, padding: '20px 16px', textAlign: 'center',
                                cursor: 'pointer', background: val ? color.bg : '#f8fafc',
                                transition: 'all 0.15s'
                            }}
                        >
                            <input type="file" accept=".xlsx,.xls" ref={ref} style={{ display: 'none' }} onChange={e => set(e.target.files[0])} />
                            <div style={{ width: 32, height: 32, borderRadius: 6, background: val ? color.iconBg : '#f1f5f9', margin: '0 auto 10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <div style={{ width: 14, height: 14, border: `2px solid ${val ? color.icon : '#94a3b8'}`, borderRadius: 2 }} />
                            </div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: val ? color.icon : '#374151', marginBottom: 2 }}>{val ? val.name : label}</div>
                            <div style={{ fontSize: 11, color: '#94a3b8' }}>
                                {val ? `${(val.size / 1024).toFixed(1)} KB` : desc}
                            </div>
                        </div>
                    ))}
                </div>
                <button
                    onClick={() => upload.mutate()}
                    disabled={!canUpload}
                    style={{
                        background: canUpload ? '#0f172a' : '#cbd5e1',
                        color: '#fff', border: 'none', borderRadius: 7,
                        padding: '10px 24px', cursor: canUpload ? 'pointer' : 'not-allowed',
                        fontWeight: 600, fontSize: 13, transition: 'background 0.15s'
                    }}
                >
                    {upload.isPending ? 'Memproses...' : 'Upload & Proses'}
                </button>
            </div>

            {/* Session history */}
            <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid #f1f5f9', fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                    Riwayat Sesi Upload
                </div>
                {!sessions.length ? (
                    <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Belum ada sesi upload.</div>
                ) : (
                    <div className="table-responsive">
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                                <tr style={{ background: '#f8fafc' }}>
                                    {['Sesi', 'Nama Batch', 'Bulan Verif', 'File MATCH', 'File BEDA', 'Match', 'Beda', 'Total', 'Status', ''].map(h => (
                                        <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {sessions.map((s, index) => (
                                    <tr key={s.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '10px 16px', fontWeight: 600, color: '#0f172a' }}>#{sessions.length - index}</td>
                                        <td style={{ padding: '10px 16px', color: '#0f172a', fontWeight: 500 }}>{s.batch_name || '—'}</td>
                                        <td style={{ padding: '10px 16px' }}>
                                            {s.bulan_verifikasi ? (
                                                <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', fontFamily: 'monospace' }}>
                                                    {s.bulan_verifikasi.slice(0,4)}/{s.bulan_verifikasi.slice(4)}
                                                </span>
                                            ) : <span style={{ color: '#cbd5e1' }}>—</span>}
                                        </td>
                                        <td style={{ padding: '10px 16px', color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.file_match_name || '—'}</td>
                                        <td style={{ padding: '10px 16px', color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.file_beda_name || '—'}</td>
                                        <td style={{ padding: '10px 16px' }}>
                                            <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: '#f0fdf4', color: '#16a34a', border: '1px solid #bbf7d0' }}>
                                                {s.total_match?.toLocaleString() ?? '—'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '10px 16px' }}>
                                            <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' }}>
                                                {s.total_beda?.toLocaleString() ?? '—'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '10px 16px', color: '#374151' }}>{s.total_records?.toLocaleString() || '—'}</td>
                                        <td style={{ padding: '10px 16px' }}>
                                            <span style={{
                                                padding: '3px 9px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                                                background: s.status === 'done' ? '#f0fdf4' : s.status === 'processing' ? '#fffbeb' : '#fef2f2',
                                                color: s.status === 'done' ? '#16a34a' : s.status === 'processing' ? '#d97706' : '#dc2626',
                                                border: `1px solid ${s.status === 'done' ? '#bbf7d0' : s.status === 'processing' ? '#fde68a' : '#fecaca'}`
                                            }}>
                                                {s.status === 'done' ? 'Selesai' : s.status === 'processing' ? 'Diproses' : s.status}
                                            </span>
                                        </td>
                                        <td style={{ padding: '10px 16px' }}>
                                            <button
                                                onClick={() => setDialog({
                                                    title: 'Hapus Sesi',
                                                    message: 'Hapus sesi ini? Data record dan progres pembagian tugas di dalam sesi ini akan ikut terhapus permanen.',
                                                    onConfirm: () => deleteSession.mutate(s.id)
                                                })}
                                                style={{ background: 'none', color: '#ef4444', border: '1px solid #fecaca', borderRadius: 5, padding: '3px 10px', cursor: 'pointer', fontSize: 11, fontWeight: 500 }}
                                            >
                                                Hapus
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}