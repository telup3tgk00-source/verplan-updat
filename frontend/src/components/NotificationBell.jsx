import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/axios'

export default function NotificationBell() {
    const [open, setOpen] = useState(false)
    const qc = useQueryClient()

    const { data: countData } = useQuery({
        queryKey: ['unread-count'],
        queryFn: () => api.get('/api/notifications/unread-count').then(r => r.data),
        refetchInterval: 30000,
        refetchIntervalInBackground: false,
        staleTime: 25000,
    })

    const { data: notifications = [] } = useQuery({
        queryKey: ['notifications'],
        queryFn: () => api.get('/api/notifications/').then(r => r.data),
        enabled: open,
    })

    const markRead = useMutation({
        mutationFn: (id) => api.patch(`/api/notifications/${id}/read`),
        onSuccess: () => {
            qc.invalidateQueries(['unread-count'])
            qc.invalidateQueries(['notifications'])
        }
    })

    const unread = countData?.count || 0

    return (
        <div style={{ position: 'relative' }}>
            <button
                onClick={() => setOpen(!open)}
                style={{
                    background: 'none', border: '1px solid #e5e7eb', borderRadius: 6,
                    cursor: 'pointer', padding: '4px 10px', fontSize: 11, fontWeight: 500,
                    color: '#64748b', display: 'flex', alignItems: 'center', gap: 6
                }}
            >
                Notifikasi
                {unread > 0 && (
                    <span style={{
                        background: '#ef4444', color: '#fff', fontSize: 9, borderRadius: 10,
                        padding: '1px 5px', fontWeight: 600, lineHeight: '14px'
                    }}>
                        {unread > 9 ? '9+' : unread}
                    </span>
                )}
            </button>

            {open && (
                <>
                    <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
                    <div style={{
                        position: 'absolute', top: 36, right: 0, width: 300, background: '#fff',
                        borderRadius: 8, boxShadow: '0 8px 30px rgba(0,0,0,0.12)', zIndex: 100,
                        border: '1px solid #e5e7eb', overflow: 'hidden'
                    }}>
                        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f1f5f9', fontWeight: 600, fontSize: 12, color: '#1e293b' }}>
                            Notifikasi
                        </div>
                        <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                            {notifications.length === 0 ? (
                                <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>Belum ada notifikasi</div>
                            ) : (
                                notifications.map(n => (
                                    <div key={n.id}
                                        onClick={() => markRead.mutate(n.id)}
                                        style={{
                                            padding: '12px 16px', borderBottom: '1px solid #f8fafc', cursor: 'pointer',
                                            background: n.is_read ? '#fff' : '#f8fafc', transition: 'background 0.15s'
                                        }}
                                    >
                                        <div style={{ fontSize: 11, fontWeight: 600, color: '#1e293b', marginBottom: 3 }}>{n.title}</div>
                                        <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.5 }}>{n.message}</div>
                                        <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 6 }}>
                                            {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
