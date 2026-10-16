import React from 'react'
import {
  LayoutDashboard,
  Film,
  PlusCircle,
  Store,
  KeyRound,
  BarChart3,
  QrCode,
  LogOut,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useTranslation } from '@/hooks/useTranslation'
import { UserProfile } from '@/types/auth'
import { Link } from 'react-router-dom'

export type MerchantTab = 'overview' | 'offers' | 'new-offer' | 'profile' | 'staff' | 'analytics'

interface MerchantSidebarProps {
  activeTab: MerchantTab
  onSelectTab: (tab: MerchantTab) => void
  user: UserProfile | null
  onLogout: () => void
  onOpenLogin: () => void
  storeName?: string
}

export const MerchantSidebar: React.FC<MerchantSidebarProps> = ({
  activeTab,
  onSelectTab,
  user,
  onLogout,
  onOpenLogin,
  storeName = "Haldiram's Sitabuldi",
}) => {
  const { t } = useTranslation()

  const navItems = [
    {
      id: 'overview' as MerchantTab,
      label: 'Live Counter',
      icon: LayoutDashboard,
      badge: 'Live',
    },
    {
      id: 'offers' as MerchantTab,
      label: 'Store Offers & Videos',
      icon: Film,
      badge: '3',
    },
    {
      id: 'new-offer' as MerchantTab,
      label: 'Post Video Offer',
      icon: PlusCircle,
    },
    {
      id: 'profile' as MerchantTab,
      label: 'Store Profile',
      icon: Store,
    },
    {
      id: 'staff' as MerchantTab,
      label: 'Counter Staff PINs',
      icon: KeyRound,
    },
    {
      id: 'analytics' as MerchantTab,
      label: 'In-Store Footfall',
      icon: BarChart3,
    },
  ]

  return (
    <aside className="w-full lg:w-64 shrink-0 space-y-4">
      {/* Store Identity Card */}
      <div className="surface-card rounded-xl p-4 border border-stone-800 bg-stone-900/90 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-stone-400 uppercase tracking-wider">
            Verified Store
          </span>
          <Badge variant="success" className="text-[9px] py-0">
            <ShieldCheck className="h-2.5 w-2.5 mr-0.5" />
            Active
          </Badge>
        </div>

        <div>
          <h3 className="font-bold text-sm text-stone-100 font-display truncate">
            {storeName}
          </h3>
          <p className="text-[11px] text-stone-400 font-mono truncate">
            Sitabuldi Main Road • Nagpur
          </p>
        </div>

        {user ? (
          <div className="pt-2 border-t border-stone-800/80 flex items-center justify-between text-xs">
            <span className="font-mono text-[11px] text-stone-400 truncate">
              {user.phone}
            </span>
            <button
              onClick={onLogout}
              className="text-stone-400 hover:text-red-400 text-[11px] font-mono transition-colors"
            >
              Sign out
            </button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs font-mono"
            onClick={onOpenLogin}
          >
            Sign in Store Owner
          </Button>
        )}
      </div>

      {/* Navigation List */}
      <nav className="surface-card rounded-xl border border-stone-800 bg-stone-900/60 p-1.5 space-y-1">
        {navItems.map((item) => {
          const isActive = activeTab === item.id
          const Icon = item.icon
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors text-left select-none ${
                isActive
                  ? 'bg-amber-500 text-stone-950 font-semibold'
                  : 'text-stone-300 hover:bg-stone-800/80 hover:text-stone-100'
              }`}
            >
              <div className="flex items-center gap-2.5 truncate">
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-stone-950' : 'text-stone-400'}`} />
                <span className="truncate">{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                    isActive
                      ? 'bg-stone-950 text-amber-400'
                      : 'bg-stone-800 text-stone-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Fast Counter Scanner Switch */}
      <Link
        to="/pos"
        className="surface-card p-3 rounded-xl border border-stone-800 bg-stone-900/40 hover:bg-stone-850 flex items-center justify-between text-xs transition-colors group block"
      >
        <div className="flex items-center gap-2">
          <QrCode className="h-4 w-4 text-amber-400" />
          <span className="font-mono text-stone-300 group-hover:text-stone-100">
            Open Counter Scanner
          </span>
        </div>
        <ChevronRight className="h-3.5 w-3.5 text-stone-500 group-hover:translate-x-0.5 transition-transform" />
      </Link>
    </aside>
  )
}
