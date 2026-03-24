import { useAuth } from '@clerk/clerk-react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { HomePage } from '@/pages/HomePage'
import { ClerkTokenBridge } from '@/components/auth/ClerkTokenBridge'

function AppShell() {
  const { isLoaded, isSignedIn } = useAuth()

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-600">
        Loading…
      </div>
    )
  }

  return (
    <>
      <ClerkTokenBridge />
      <Routes>
        <Route
          path="/login"
          element={isSignedIn ? <Navigate to="/" replace /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={isSignedIn ? <Navigate to="/" replace /> : <RegisterPage />}
        />
        <Route
          path="/"
          element={isSignedIn ? <MainLayout /> : <Navigate to="/login" replace />}
        >
          <Route index element={<HomePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return <AppShell />
}
