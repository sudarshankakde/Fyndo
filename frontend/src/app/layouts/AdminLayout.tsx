import React, { useEffect, useRef } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { ShieldAlert, LogOut } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { logout } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { IDLE_LOCK_TIMEOUT_MS } from '@/config/constants'

export const AdminLayout: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { refreshToken } = useAppSelector((state) => state.auth)
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 15-Minute Admin Idle Lock Timer as mandated by Section 4.3
  useEffect(() => {
    const resetIdleTimer = () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      idleTimerRef.current = setTimeout(async () => {
        await authService.logout(refreshToken)
        dispatch(logout())
        navigate('/admin/login')
      }, IDLE_LOCK_TIMEOUT_MS.ADMIN)
    }

    const events = ['mousedown', 'mousemove', 'keypress', 'touchstart', 'scroll']
    events.forEach((evt) => window.addEventListener(evt, resetIdleTimer))
    resetIdleTimer()

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current)
      events.forEach((evt) => window.removeEventListener(evt, resetIdleTimer))
    }
  }, [dispatch, navigate, refreshToken])

  const handleLogout = async () => {
    await authService.logout(refreshToken)
    dispatch(logout())
    navigate('/admin/login')
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-sans text-stone-900">
      <header className="bg-white border-b border-stone-200 px-6 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-stone-900 text-white flex items-center justify-center font-bold text-sm">
            FD
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-stone-900 tracking-tight">Admin Desk</h1>
            <p className="text-[11px] font-semibold text-stone-500">Video Moderation & Compliance</p>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-stone-600 hover:text-stone-900 bg-stone-100 hover:bg-stone-200 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Log out</span>
        </button>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
