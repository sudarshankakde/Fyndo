import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Store, Film, Ticket, ShieldAlert, RefreshCw } from 'lucide-react'
import { adminService, AdminStatsResponse } from '@/services/adminService'

export const AdminStatsOverview: React.FC = () => {
  const { data: stats, isLoading, refetch } = useQuery<AdminStatsResponse>({
    queryKey: ['admin-stats'],
    queryFn: () => adminService.getStats(),
  })

  if (isLoading) {
    return (
      <div className="py-8 text-center space-y-2 font-sans">
        <RefreshCw className="w-6 h-6 text-primary animate-spin mx-auto" />
        <p className="text-xs text-stone-500 font-medium">Loading platform metrics...</p>
      </div>
    )
  }

  const items = [
    {
      label: 'Total Registered Users',
      value: stats?.total_users ?? 0,
      subtext: 'Shoppers & Merchant Owners',
      icon: Users,
      color: 'text-stone-900',
    },
    {
      label: 'Merchant Stores',
      value: stats?.total_merchants ?? 0,
      subtext: 'Local retail storefronts',
      icon: Store,
      color: 'text-primary',
    },
    {
      label: 'Live Active Deals',
      value: stats?.active_reels ?? 0,
      subtext: `${stats?.total_reels ?? 0} total uploaded`,
      icon: Film,
      color: 'text-amber-600',
    },
    {
      label: 'Pending Reel Review',
      value: stats?.pending_moderation_count ?? 0,
      subtext: 'Awaiting admin clearance',
      icon: ShieldAlert,
      color: 'text-rose-600',
    },
    {
      label: 'Counter Redemptions',
      value: stats?.total_redemptions ?? 0,
      subtext: 'Verified in-store scans',
      icon: Ticket,
      color: 'text-emerald-700',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-sans">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <div
            key={item.label}
            className="bg-white p-5 rounded-3xl border border-stone-200/80 shadow-2xs space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-400">
                {item.label}
              </span>
              <Icon className={`w-4 h-4 ${item.color}`} />
            </div>
            <p className="text-3xl font-black text-stone-900 font-mono">{item.value}</p>
            <p className="text-[11px] text-stone-500">{item.subtext}</p>
          </div>
        )
      })}
    </div>
  )
}
