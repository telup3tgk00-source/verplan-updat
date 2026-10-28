import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore, canAccess } from './store/authStore'
import LoginPage from './pages/LoginPage'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import VerifikasiPage from './pages/VerifikasiPage'
import AssignmentPage from './pages/AssignmentPage'
import ProgressPage from './pages/ProgressPage'
import ExportPage from './pages/ExportPage'
import UsersPage from './pages/UsersPage'
import AuditPage from './pages/AuditPage'

function ProtectedRoute({ children, menu }) {
  const { role } = useAuthStore()
  if (!role) return <Navigate to="/login" replace />
  if (menu && !canAccess(role, menu)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="upload" element={
            <ProtectedRoute menu="upload"><UploadPage /></ProtectedRoute>
          } />
          <Route path="verifikasi" element={
            <ProtectedRoute menu="verifikasi"><VerifikasiPage /></ProtectedRoute>
          } />
          <Route path="assignment" element={
            <ProtectedRoute menu="pembagian"><AssignmentPage /></ProtectedRoute>
          } />
          <Route path="progress" element={
            <ProtectedRoute menu="progres"><ProgressPage /></ProtectedRoute>
          } />
          <Route path="export" element={
            <ProtectedRoute menu="export"><ExportPage /></ProtectedRoute>
          } />
          <Route path="users" element={
            <ProtectedRoute menu="settings"><UsersPage /></ProtectedRoute>
          } />
          <Route path="audit" element={
            <ProtectedRoute menu="audit"><AuditPage /></ProtectedRoute>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}