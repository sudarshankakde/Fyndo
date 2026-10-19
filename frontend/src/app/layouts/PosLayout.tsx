import React, { useEffect, useRef } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { QrCode, LogOut, ShieldAlert } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { logout } from '@/store/slices/authSlice'
import { IDLE_LOCK_TIMEOUT_MS } from '@/config/constants'

export const PosLayout: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { staff } = useAppSelector((state) => state.auth)
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 10-Minute Idle Lock Timer as mandated by Section 4.3
  useEffect(() => {
    const resetIdleTimer = () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      idleTimerRef.current = setTimeout(() => {
        dispatch(logout())
        navigate('/pos/login')
      }, IDLE_LOCK_TIMEOUT_MS.POS)
    }

    const events = ['mousedown', 'mousemove', 'keypress', 'touchstart', 'scroll']
    events.forEach((evt) => window.addEventListener(evt, resetIdleTimer))
    resetIdleTimer()

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      events.forEach((evt) => window.removeEventListener(evt, resetIdleTimer))
    }
  }, [dispatch, navigate])

  const handleLogout = () => {
    dispatch(logout())
    navigate('/pos/login')
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-sans text-stone-900">
      {/* POS Top Bar */}
      <header className="bg-white border-b border-stone-200 px-4 sm:px-6 py-3 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
            <QrCode className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-stone-900 tracking-tight">Counter Scanner</h1>
            <p className="text-[11px] font-semibold text-stone-500">
              {staff?.businessName || 'Store POS'} • Cashier: {staff?.staffName || 'Staff'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Scanner Ready
          </span>

          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Lock Terminal</span>
          </button>
        </div>
      </header>

      {/* Main Scanner Workspace */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-6 flex flex-col justify-center">
        <Outlet />
      </main>
    </div>
  )
}
