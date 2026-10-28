import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
    persist(
        (set) => ({
            role: null,
            user: null,
            kode_unit: null,
            setAuth: (role, full_name, kode_unit) => set({
                role,
                kode_unit: kode_unit || null,
                user: { full_name }
            }),
            logout: () => set({ role: null, user: null, kode_unit: null }),
        }),
        { name: 'auth-storage' }
    )
)

// Helper untuk cek apakah role punya akses ke menu tertentu
export const MENU_ACCESS = {
    super_admin: ['dashboard', 'upload', 'pembagian', 'progres', 'export', 'settings', 'verifikasi', 'audit'],
    uid:         ['dashboard', 'progres', 'export', 'settings', 'verifikasi'],
    up3:         ['dashboard', 'upload', 'progres', 'export', 'settings', 'verifikasi'],
    ulp:         ['dashboard', 'pembagian', 'progres', 'settings', 'export', 'verifikasi'],
    verifikator: ['dashboard', 'verifikasi'],
}

export const canAccess = (role, menu) => {
    if (!role) return false
    const allowed = MENU_ACCESS[role] || []
    return allowed.includes(menu)
}