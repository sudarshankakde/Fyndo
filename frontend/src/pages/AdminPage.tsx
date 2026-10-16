import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutDashboard, ShieldCheck, Film, Store, LogOut, Clock } from 'lucide-react'
import { AdminStatsOverview } from '@/components/admin/AdminStatsOverview'
import { AdminKycQueueView } from '@/components/admin/AdminKycQueueView'
import { AdminReelModerationView } from '@/components/admin/AdminReelModerationView'
import { AdminMerchantDirectoryView } from '@/components/admin/AdminMerchantDirectoryView'
import { IDLE_LOCK_TIMEOUT_MS } from '@/config/constants'
import { useAppDispatch } from '@/store'
import { logout } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'

type AdminTab = 'STATS' | 'KYC' | 'REELS' | 'MERCHANTS'

export const AdminPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [activeTab, setActiveTab] = useState<AdminTab>('STATS')

  // 15-minute Idle Lock / Auto-logout for Super Admin Desk
  useEffect(() => {
    let idleTimer: ReturnType<typeof setTimeout>

    const resetIdleTimer = () => {
      clearTimeout(idleTimer)
      idleTimer = setTimeout(async () => {
        await authService.logout()
        dispatch(logout())
        navigate('/admin/login?reason=idle')
      }, IDLE_LOCK_TIMEOUT_MS.ADMIN)
    }

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart']
    events.forEach((ev) => window.addEventListener(ev, resetIdleTimer))
    resetIdleTimer()

    return () => {
      clearTimeout(idleTimer)
      events.forEach((ev) => window.removeEventListener(ev, resetIdleTimer))
    }
  }, [dispatch, navigate])

  const handleLogout = async () => {
    await authService.logout()
    dispatch(logout())
    navigate('/admin/login')
  }

  const tabs = [
    { id: 'STATS' as AdminTab, label: 'Platform Metrics', icon: LayoutDashboard },
    { id: 'KYC' as AdminTab, label: 'Store KYC Queue', icon: ShieldCheck },
    { id: 'REELS' as AdminTab, label: 'Reel Moderation', icon: Film },
    { id: 'MERCHANTS' as AdminTab, label: 'Merchant Directory', icon: Store },
  ]

  return (
    <div className="space-y-6 font-sans text-stone-900 pb-16">
      {/* Top Admin Desk Header */}
      <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-stone-500 uppercase tracking-wider">
              Super Admin Desk (Pilot Beta)
            </span>
          </div>
          <h1 className="text-2xl font-black text-stone-900 tracking-tight">
            Compliance & Verification Console
          </h1>
          <p className="text-xs text-stone-500 mt-0.5">
            Audit merchant registration proofs, video copyright compliance, and platform transaction volume.
          </p>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-stone-200 hover:bg-red-50 hover:border-red-200 text-stone-600 hover:text-red-700 text-xs font-bold transition-all"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Exit Admin Desk</span>
        </button>
      </div>

      {/* Admin Tab Navigation */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-stone-200 no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold transition-all shrink-0 ${
                isActive
                  ? 'bg-stone-900 text-white shadow-xs'
                  : 'bg-white text-stone-600 hover:text-stone-900 border border-stone-200/80 hover:bg-stone-50'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Active Tab View */}
      <div className="pt-2">
        {activeTab === 'STATS' && <AdminStatsOverview />}
        {activeTab === 'KYC' && <AdminKycQueueView />}
        {activeTab === 'REELS' && <AdminReelModerationView />}
        {activeTab === 'MERCHANTS' && <AdminMerchantDirectoryView />}
      </div>
    </div>
  )
}
