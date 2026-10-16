import React from 'react'
import { Store, Users, Film, TicketCheck, IndianRupee } from 'lucide-react'
import { AdminStats } from '@/services/adminService'

interface AdminStatsOverviewProps {
  stats: AdminStats | null
}

export const AdminStatsOverview: React.FC<AdminStatsOverviewProps> = ({ stats }) => {
  if (!stats) return null

  const cards = [
    {
      label: 'Active Stores',
      value: stats.total_merchants,
      icon: Store,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10 border-sky-500/20',
    },
    {
      label: 'Shoppers',
      value: stats.total_users,
      icon: Users,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      label: 'Video Reels',
      value: stats.total_reels,
      icon: Film,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10 border-purple-500/20',
    },
    {
      label: 'Redemptions',
      value: stats.total_redemptions,
      icon: TicketCheck,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      label: 'Savings Given',
      value: `₹${stats.total_discount_applied.toLocaleString('en-IN')}`,
      icon: IndianRupee,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10 border-rose-500/20',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map((c) => {
        const Icon = c.icon
        return (
          <div
            key={c.label}
            className={`p-3.5 rounded-2xl border ${c.bg} flex flex-col justify-between gap-2 shadow-sm`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                {c.label}
              </span>
              <Icon className={`h-4 w-4 ${c.color}`} />
            </div>
            <div className={`text-xl font-extrabold ${c.color}`}>{c.value}</div>
          </div>
        )
      })}
    </div>
  )
}
