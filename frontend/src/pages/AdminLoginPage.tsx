import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useAppDispatch } from '@/store'
import { setAuthSession } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'

export const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!identifier.trim() || !password.trim()) {
      setErrorMessage('Please enter your admin identifier and password.')
      return
    }

    setIsLoading(true)
    setErrorMessage(null)

    try {
      const session = await authService.adminLogin({
        identifier: identifier.trim(),
        password,
      })
      dispatch(setAuthSession(session))
      navigate('/admin')
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid administrator credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-stone-900 flex flex-col justify-between p-4 sm:p-6 font-sans">
      <header className="max-w-sm w-full mx-auto flex items-center justify-between pb-2">
        <Link to="/login" className="flex items-center gap-1.5 text-xs font-bold text-stone-500 hover:text-stone-900">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Login</span>
        </Link>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-stone-100 text-stone-700 border border-stone-200">
          Admin Portal
        </span>
      </header>

      <main className="max-w-sm w-full mx-auto my-auto py-2">
        <div className="bg-white rounded-3xl border border-stone-200 p-6 sm:p-8 shadow-card space-y-5">
          <div className="text-center">
            <div className="w-12 h-12 rounded-2xl bg-stone-900 text-white flex items-center justify-center mx-auto mb-3 shadow-md">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-extrabold text-stone-900 tracking-tight">Admin Desk Login</h1>
            <p className="text-xs text-stone-500 mt-1">Authorized platform administrators only.</p>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-stone-600 uppercase tracking-wider block">Admin Identifier</label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="admin@fyndo.local"
                className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-900 shadow-2xs"
                autoFocus
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-stone-600 uppercase tracking-wider block">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-900/20 focus:border-stone-900 shadow-2xs"
              />
            </div>

            <Button type="submit" isLoading={isLoading} className="w-full py-3 bg-stone-900 hover:bg-stone-800 text-white">
              Log in to Admin Desk
            </Button>
          </form>
        </div>
      </main>

      <footer className="max-w-sm w-full mx-auto text-center text-[11px] font-medium text-stone-400">
        Fyndo Administrative Operations
      </footer>
    </div>
  )
}
