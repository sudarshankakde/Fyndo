import React, { useEffect, useState } from 'react'
import { ShieldCheck, RefreshCw, AlertCircle, LayoutDashboard, Film, Store, ShieldAlert } from 'lucide-react'
import {
  adminService,
  AdminPendingReel,
  AdminStats,
  AdminMerchantItem,
} from '@/services/adminService'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { AdminStatsOverview } from '@/components/admin/AdminStatsOverview'
import { AdminModerationDesk } from '@/components/admin/AdminModerationDesk'
import { AdminMerchantsDesk } from '@/components/admin/AdminMerchantsDesk'
import { AdminReelsDesk } from '@/components/admin/AdminReelsDesk'

type AdminTab = 'overview' | 'moderation' | 'merchants' | 'reels'

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('overview')
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [pendingReels, setPendingReels] = useState<AdminPendingReel[]>([])
  const [allReels, setAllReels] = useState<AdminPendingReel[]>([])
  const [merchants, setMerchants] = useState<AdminMerchantItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [statsData, pendingData, allReelsData, merchantsData] = await Promise.all([
        adminService.getStats().catch(() => null),
        adminService.getPendingReels().catch(() => []),
        adminService.getAllReels().catch(() => []),
        adminService.getMerchants().catch(() => []),
      ])
      if (statsData) setStats(statsData)
      setPendingReels(pendingData)
      setAllReels(allReelsData)
      setMerchants(merchantsData)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load administrative data')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  return (
    <div className="min-h-screen pb-24 pt-4 max-w-4xl mx-auto px-4 space-y-5">
      {/* Top Header */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="amber" className="text-xs font-bold py-0.5">
              Super Admin Operations
            </Badge>
            <span className="text-xs text-slate-400">Regional Data Hub</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white font-heading">Operations Portal</h1>
          <p className="text-xs text-slate-400">
            Control center for store onboarding, video moderation, offers, and cashier terminals.
          </p>
        </div>

        <Button variant="ghost" size="sm" onClick={loadData} className="text-slate-400">
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Cards Banner */}
      <AdminStatsOverview stats={stats} />

      {/* Tabs Switcher */}
      <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-slate-900 border border-slate-800 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'overview' ? 'bg-amber-400 text-slate-900 shadow-sm' : 'text-slate-400 hover:text-white'
          }`}
        >
          <LayoutDashboard className="h-3.5 w-3.5" />
          Overview
        </button>

        <button
          onClick={() => setActiveTab('moderation')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all relative ${
            activeTab === 'moderation' ? 'bg-amber-400 text-slate-900 shadow-sm' : 'text-slate-400 hover:text-white'
          }`}
        >
          <ShieldAlert className="h-3.5 w-3.5" />
          Moderation Desk
          {pendingReels.length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500 text-white font-black">
              {pendingReels.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('merchants')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'merchants' ? 'bg-amber-400 text-slate-900 shadow-sm' : 'text-slate-400 hover:text-white'
          }`}
        >
          <Store className="h-3.5 w-3.5" />
          Stores ({merchants.length})
        </button>

        <button
          onClick={() => setActiveTab('reels')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'reels' ? 'bg-amber-400 text-slate-900 shadow-sm' : 'text-slate-400 hover:text-white'
          }`}
        >
          <Film className="h-3.5 w-3.5" />
          Reels & Offers ({allReels.length})
        </button>
      </div>

      {/* Main Tab Views */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
          <p className="text-xs text-slate-400">Loading operations data...</p>
        </div>
      ) : activeTab === 'moderation' ? (
        <AdminModerationDesk reels={pendingReels} onRefresh={loadData} />
      ) : activeTab === 'merchants' ? (
        <AdminMerchantsDesk merchants={merchants} onRefresh={loadData} />
      ) : activeTab === 'reels' ? (
        <AdminReelsDesk reels={allReels} merchants={merchants} onRefresh={loadData} />
      ) : (
        <div className="space-y-6">
          <AdminModerationDesk reels={pendingReels} onRefresh={loadData} />
          <AdminMerchantsDesk merchants={merchants} onRefresh={loadData} />
        </div>
      )}
    </div>
  )
}
