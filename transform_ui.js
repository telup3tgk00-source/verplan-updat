import fs from 'fs';

const filePath = 'frontend/src/pages/VerifikasiPage.jsx';
let content = fs.readFileSync(filePath, 'utf-8');

// 1. Add Lucide imports at top
const importTarget = "import { useAuthStore } from '../store/authStore'";
const lucideImports = `import { useAuthStore } from '../store/authStore'
import {
    Camera, CheckCircle2, Clock, AlertTriangle, XCircle, FileCheck, Edit3,
    Search, ChevronLeft, ChevronRight, RefreshCw, Shield, ShieldCheck, Key,
    Bot, User, TrendingUp, TrendingDown, Layers, HelpCircle, RotateCcw, X,
    Info, Tag, Building2, Hash, FileText, Sparkles, ArrowUpDown, Check, Copy,
    CheckSquare2, Zap, SlidersHorizontal
} from 'lucide-react'`;

if (!content.includes('lucide-react')) {
    content = content.replace(importTarget, lucideImports);
}

// 2. Update Badge component to include icons
const oldBadge = `function Badge({ status }) {
    const s = STATUS_STYLE[status] || STATUS_STYLE.PENDING
    return (
        <span style={{ padding: '3px 9px', borderRadius: 4, fontSize: 11, fontWeight: 500, background: s.bg, color: s.color, border: \`1px solid \${s.border}\` }}>
            {STATUS_LABEL[status] || status}
        </span>
    )
}`;

const newBadge = `function Badge({ status }) {
    const s = STATUS_STYLE[status] || STATUS_STYLE.PENDING
    let Icon = Clock
    if (status === 'VERIFIED_OK') Icon = CheckCircle2
    else if (status === 'VERIFIED_REJECT') Icon = XCircle
    else if (status === 'NEED_INVESTIGATION') Icon = AlertTriangle

    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '4px 9px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            background: s.bg, color: s.color, border: \`1px solid \${s.border}\`,
            lineHeight: 1.2
        }}>
            <Icon size={12} strokeWidth={2.5} />
            {STATUS_LABEL[status] || status}
        </span>
    )
}`;

if (content.includes(oldBadge)) {
    content = content.replace(oldBadge, newBadge);
}

// 3. Update Table header
const oldThMap = `{['Unit', 'ID Pelanggan', 'Kode Biller', 'Stand AI', 'Stand Biller', 'Selisih', 'Merek AI / Biller', 'LBKB', 'Alasan', 'Status', 'Foto', ''].map(h => (`;

const newThMap = `{[
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
))}`;

// Replace the table header map block
const theadRegex = /\{\['Unit', 'ID Pelanggan', 'Kode Biller', 'Stand AI', 'Stand Biller', 'Selisih', 'Merek AI \/ Biller', 'LBKB', 'Alasan', 'Status', 'Foto', ''\]\.map\(h => \([\s\S]*?<\/th>\s*\)\)\}/;
if (theadRegex.test(content)) {
    content = content.replace(theadRegex, newThMap);
}

// 4. Update Action buttons in rows:
// Change Foto button
const oldFotoBtn = `<button
                                                onClick={() => setExpandedFoto(expandedFoto === r.id_pelanggan ? null : r.id_pelanggan)}
                                                style={{
                                                    background: expandedFoto === r.id_pelanggan ? '#dbeafe' : '#f1f5f9',
                                                    color: '#1d4ed8', border: '1px solid #bfdbfe', borderRadius: 5,
                                                    padding: '4px 10px', cursor: 'pointer', fontSize: 11, fontWeight: 500
                                                }}
                                            >
                                                📷 Foto
                                            </button>`;

const newFotoBtn = `<button
                                                onClick={() => setExpandedFoto(expandedFoto === r.id_pelanggan ? null : r.id_pelanggan)}
                                                title="Lihat Foto Meter"
                                                style={{
                                                    display: 'inline-flex', alignItems: 'center', gap: 5,
                                                    background: expandedFoto === r.id_pelanggan ? '#dbeafe' : '#f8fafc',
                                                    color: '#1d4ed8', border: '1px solid #bfdbfe', borderRadius: 6,
                                                    padding: '5px 10px', cursor: 'pointer', fontSize: 11, fontWeight: 600,
                                                    transition: 'all 0.15s ease'
                                                }}
                                            >
                                                <Camera size={13} />
                                                <span>Foto</span>
                                            </button>`;

if (content.includes(oldFotoBtn)) {
    content = content.replace(oldFotoBtn, newFotoBtn);
}

// Change Kerjakan button to modern icon button
const oldKerjakanBtn = `<button
                                                onClick={() => openModal(r)}
                                                style={{ background: '#f1f5f9', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 5, padding: '4px 12px', cursor: 'pointer', fontSize: 11, fontWeight: 500 }}
                                            >
                                                Kerjakan
                                            </button>`;

const newKerjakanBtn = `<button
                                                onClick={() => openModal(r)}
                                                title="Kerjakan Verifikasi Data"
                                                style={{
                                                    display: 'inline-flex', alignItems: 'center', gap: 6,
                                                    background: '#4f46e5', color: '#fff', border: 'none',
                                                    borderRadius: 6, padding: '6px 12px', cursor: 'pointer',
                                                    fontSize: 11, fontWeight: 600,
                                                    boxShadow: '0 1px 3px rgba(79, 70, 229, 0.25)',
                                                    transition: 'all 0.15s ease'
                                                }}
                                                onMouseEnter={e => e.currentTarget.style.background = '#4338ca'}
                                                onMouseLeave={e => e.currentTarget.style.background = '#4f46e5'}
                                            >
                                                <FileCheck size={13} />
                                                <span>Verifikasi</span>
                                            </button>`;

if (content.includes(oldKerjakanBtn)) {
    content = content.replace(oldKerjakanBtn, newKerjakanBtn);
}

// 5. Update pagination buttons with icons
const oldPagination = `<div style={{ padding: '10px 16px', borderTop: '1px solid #f1f5f9', display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'flex-end' }}>
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                        style={{ padding: '4px 12px', border: '1px solid #e2e8f0', borderRadius: 5, cursor: page === 1 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, color: '#374151', opacity: page === 1 ? 0.4 : 1 }}>
                        Sebelumnya
                    </button>
                    <span style={{ color: '#64748b', fontSize: 12 }}>Hal. {page}</span>
                    <button onClick={() => setPage(p => p + 1)} disabled={records.length < 20}
                        style={{ padding: '4px 12px', border: '1px solid #e2e8f0', borderRadius: 5, cursor: records.length < 20 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, color: '#374151', opacity: records.length < 20 ? 0.4 : 1 }}>
                        Berikutnya
                    </button>
                </div>`;

const newPagination = `<div style={{ padding: '12px 18px', borderTop: '1px solid #f1f5f9', display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'flex-end', background: '#fafbfc' }}>
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 12px', border: '1px solid #e2e8f0', borderRadius: 6, cursor: page === 1 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, fontWeight: 500, color: '#374151', opacity: page === 1 ? 0.4 : 1 }}>
                        <ChevronLeft size={14} />
                        <span>Sebelumnya</span>
                    </button>
                    <span style={{ color: '#64748b', fontSize: 12, fontWeight: 600 }}>Halaman {page}</span>
                    <button onClick={() => setPage(p => p + 1)} disabled={records.length < 20}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '5px 12px', border: '1px solid #e2e8f0', borderRadius: 6, cursor: records.length < 20 ? 'not-allowed' : 'pointer', background: '#fff', fontSize: 12, fontWeight: 500, color: '#374151', opacity: records.length < 20 ? 0.4 : 1 }}>
                        <span>Berikutnya</span>
                        <ChevronRight size={14} />
                    </button>
                </div>`;

if (content.includes(oldPagination)) {
    content = content.replace(oldPagination, newPagination);
}

// 6. Update Header & Filter Toolbar
const oldHeader = `<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
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
                                {s.batch_name ? s.batch_name : \`Sesi #\${s.id}\`} ({new Date(s.created_at).toLocaleDateString('id-ID')})
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
            </div>`;

const newHeader = `<div style={{ marginBottom: 18 }}>
                {/* Title Bar */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 12 }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ background: '#eef2ff', color: '#4f46e5', width: 34, height: 34, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <CheckSquare2 size={19} />
                            </div>
                            <div>
                                <h1 style={{ fontSize: 19, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.3px', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                                    Verifikasi Data BEDA
                                    <span style={{ fontSize: 11, fontWeight: 700, color: '#4f46e5', background: '#eef2ff', border: '1px solid #c7d2fe', padding: '1px 8px', borderRadius: 4 }}>
                                        AI ≠ Biller
                                    </span>
                                </h1>
                                <p style={{ fontSize: 12, color: '#64748b', margin: '2px 0 0 0' }}>Kerjakan data anomali stand meter & verifikasi foto fisik</p>
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <button
                            type="button"
                            onClick={() => {
                                qc.invalidateQueries(['records'])
                                toast.success('Memperbarui data verifikasi...')
                            }}
                            title="Segarkan data tabel"
                            style={{
                                display: 'inline-flex', alignItems: 'center', gap: 6,
                                padding: '6px 12px', background: '#fff', border: '1px solid #e2e8f0',
                                borderRadius: 6, color: '#475569', fontSize: 12, fontWeight: 600,
                                cursor: 'pointer', boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                            }}
                        >
                            <RefreshCw size={13} />
                            <span>Refresh</span>
                        </button>
                    </div>
                </div>

                {/* Modern Filters Toolbar */}
                <div style={{
                    background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 10,
                    padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        {/* Search ID Pelanggan */}
                        <div style={{ position: 'relative' }}>
                            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                            <input
                                placeholder="Cari ID Pelanggan..."
                                value={filter.search}
                                onChange={e => { setFilter(f => ({ ...f, search: e.target.value })); setPage(1) }}
                                style={{ ...inputStyle, width: 160, paddingLeft: 30 }}
                            />
                        </div>

                        {/* Search Unit UP */}
                        <div style={{ position: 'relative' }}>
                            <Building2 size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                            <input
                                placeholder="Cari Unit UP..."
                                value={filter.unit}
                                onChange={e => { setFilter(f => ({ ...f, unit: e.target.value })); setPage(1) }}
                                style={{ ...inputStyle, width: 120, paddingLeft: 28 }}
                            />
                        </div>

                        {/* Toggle Anomali */}
                        <button
                            type="button"
                            onClick={() => setFilter(f => ({ ...f, anomalyOnly: !f.anomalyOnly }))}
                            style={{
                                display: 'inline-flex', alignItems: 'center', gap: 5,
                                padding: '6px 11px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                                border: filter.anomalyOnly ? '1.5px solid #f59e0b' : '1px solid #cbd5e1',
                                background: filter.anomalyOnly ? '#fffbeb' : '#fff',
                                color: filter.anomalyOnly ? '#b45309' : '#475569',
                                cursor: 'pointer', transition: 'all 0.15s ease'
                            }}
                        >
                            <AlertTriangle size={13} color={filter.anomalyOnly ? '#b45309' : '#94a3b8'} />
                            <span>Anomali</span>
                        </button>

                        {/* Toggle Merek Beda */}
                        <button
                            type="button"
                            onClick={() => setFilter(f => ({ ...f, merekMismatch: !f.merekMismatch }))}
                            style={{
                                display: 'inline-flex', alignItems: 'center', gap: 5,
                                padding: '6px 11px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                                border: filter.merekMismatch ? '1.5px solid #6366f1' : '1px solid #cbd5e1',
                                background: filter.merekMismatch ? '#eef2ff' : '#fff',
                                color: filter.merekMismatch ? '#4338ca' : '#475569',
                                cursor: 'pointer', transition: 'all 0.15s ease'
                            }}
                        >
                            <Layers size={13} color={filter.merekMismatch ? '#4338ca' : '#94a3b8'} />
                            <span>Merek Beda</span>
                        </button>

                        {/* Filter Selisih */}
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: '#f8fafc', padding: '3px 8px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                            <SlidersHorizontal size={12} color="#64748b" />
                            <span style={{ fontSize: 10, color: '#64748b', fontWeight: 700 }}>SELISIH:</span>
                            <input
                                type="number"
                                placeholder="Min"
                                value={filter.minSelisih}
                                onChange={e => { setFilter(f => ({ ...f, minSelisih: e.target.value })); setPage(1) }}
                                style={{ ...inputStyle, width: 50, height: 26, fontSize: 11, padding: '0 6px', border: '1px solid #cbd5e1', boxShadow: 'none' }}
                            />
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>s/d</span>
                            <input
                                type="number"
                                placeholder="Max"
                                value={filter.maxSelisih}
                                onChange={e => { setFilter(f => ({ ...f, maxSelisih: e.target.value })); setPage(1) }}
                                style={{ ...inputStyle, width: 50, height: 26, fontSize: 11, padding: '0 6px', border: '1px solid #cbd5e1', boxShadow: 'none' }}
                            />
                        </div>

                        {/* Reset Filter Button */}
                        {(filter.search || filter.unit || filter.anomalyOnly || filter.merekMismatch || filter.minSelisih || filter.maxSelisih || filter.status || filter.reasonType || filter.sessionId || filter.lbkb.length > 0) && (
                            <button
                                type="button"
                                onClick={() => setFilter({ status: '', search: '', anomalyOnly: false, merekMismatch: false, sessionId: '', unit: '', reasonType: '', lbkb: [], minSelisih: '', maxSelisih: '' })}
                                title="Reset semua filter"
                                style={{
                                    display: 'inline-flex', alignItems: 'center', gap: 4,
                                    padding: '5px 9px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                                    border: '1px solid #fecaca', background: '#fef2f2', color: '#b91c1c',
                                    cursor: 'pointer'
                                }}
                            >
                                <RotateCcw size={12} />
                                <span>Reset</span>
                            </button>
                        )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', borderTop: '1px dashed #f1f5f9', paddingTop: 8 }}>
                        {/* Dropdown Sesi */}
                        <select
                            value={filter.sessionId}
                            onChange={e => { setFilter(f => ({ ...f, sessionId: e.target.value })); setPage(1) }}
                            style={{ ...inputStyle, paddingLeft: 10, maxWidth: 200 }}
                        >
                            <option value="">{role === 'verifikator' ? 'Semua Tugas Saya' : 'Semua Sesi Batch'}</option>
                            {sessions.map(s => (
                                <option key={s.id} value={s.id}>
                                    {s.batch_name ? s.batch_name : \`Sesi #\${s.id}\`} ({new Date(s.created_at).toLocaleDateString('id-ID')})
                                </option>
                            ))}
                        </select>

                        {/* Dropdown Status */}
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

                        {/* Dropdown Alasan */}
                        <select
                            value={filter.reasonType}
                            onChange={e => { setFilter(f => ({ ...f, reasonType: e.target.value })); setPage(1) }}
                            style={{ ...inputStyle, paddingLeft: 10, maxWidth: 170 }}
                        >
                            <option value="">Semua Alasan</option>
                            {reasons.map(r => (
                                <option key={r.value} value={r.value}>{r.label}</option>
                            ))}
                        </select>

                        {/* Dropdown LBKB */}
                        <MultiSelectDropdown
                            options={lbkbOptions}
                            selected={filter.lbkb}
                            onChange={vals => { setFilter(f => ({ ...f, lbkb: vals })); setPage(1); }}
                            placeholder="Semua LBKB"
                        />
                    </div>
                </div>
            </div>`;

if (content.includes(oldHeader)) {
    content = content.replace(oldHeader, newHeader);
}

// 7. Modal Pengerjaan: add icons to buttons
const oldModalBtns = `<div className="grid-upload" style={{ marginTop: 'auto', marginBottom: 0 }}>
                                                <button onClick={() => handleVerify('VERIFIED_OK')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#16a34a', color: '#fff' }}>{isOverrideMode ? 'Simpan Revisi' : '✓ Selesai / OK'}</button>
                                                <button onClick={() => handleVerify('NEED_INVESTIGATION')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#d97706', color: '#fff' }}>{isOverrideMode ? 'Ubah ke Investigasi' : '⚑ Perlu Investigasi'}</button>
                                            </div>`;

const newModalBtns = `<div className="grid-upload" style={{ marginTop: 'auto', marginBottom: 0, gap: 10 }}>
                                                <button onClick={() => handleVerify('VERIFIED_OK')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#16a34a', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                                    <CheckCircle2 size={16} />
                                                    <span>{isOverrideMode ? 'Simpan Revisi' : 'Selesai / OK'}</span>
                                                </button>
                                                <button onClick={() => handleVerify('NEED_INVESTIGATION')} disabled={verifyMutation.isPending}
                                                    style={{ ...btnBase, background: '#d97706', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                                    <AlertTriangle size={16} />
                                                    <span>{isOverrideMode ? 'Ubah ke Investigasi' : 'Perlu Investigasi'}</span>
                                                </button>
                                            </div>`;

if (content.includes(oldModalBtns)) {
    content = content.replace(oldModalBtns, newModalBtns);
}

fs.writeFileSync(filePath, content, 'utf-8');
console.log('UI transformation script finished successfully!');

