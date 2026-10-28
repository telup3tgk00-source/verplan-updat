import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
    baseURL: import.meta.env.PROD ? '' : (import.meta.env.VITE_API_URL ?? 'http://localhost:8000'),
    withCredentials: true // JWT akan dikirim via HTTP-Only cookie secara otomatis
})

// Interceptor request sudah tidak diperlukan karena token lewat cookie


// Deduplikasi toast "server tidak terhubung" — 1x per 10 detik
// Mencegah spam notif saat banyak request gagal bersamaan (network blip)
let _lastNetworkErrToast = 0
const NETWORK_ERR_COOLDOWN = 10_000 // ms

api.interceptors.response.use(
    res => res,
    err => {
        if (!err.response) {
            // Network error / server down / request dibatalkan browser
            const now = Date.now()
            if (now - _lastNetworkErrToast > NETWORK_ERR_COOLDOWN) {
                _lastNetworkErrToast = now
                import('sonner').then(({ toast }) => {
                    toast.error('Server tidak terhubung. Periksa koneksi internet Anda.', {
                        id: 'network-error', // ID unik: sonner skip duplikat
                        duration: 4000,
                    })
                })
            }
        } else if (err.response?.status === 401) {
            useAuthStore.getState().logout()
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
        }
        return Promise.reject(err)
    }
)

export default api