import React from 'react'
import { LogOut, User, ShieldCheck, QrCode, Store, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { useAppDispatch, useAppSelector } from '@/store'
import { logout } from '@/store/slices/authSlice'
import { RoleSwitcher } from '@/components/common/RoleSwitcher'

interface AuthenticatedHeaderProps {
  currentPortalName: string
}

export const AuthenticatedHeader: React.FC<AuthenticatedHeaderProps> = ({ currentPortalName }) => {
  const dispatch = useAppDispatch()
  const { user, staff } = useAppSelector((state) => state.auth)

  const handleLogout = () => {
    dispatch(logout())
  }

  const roleLabel = staff
    ? 'Counter Cashier'
    : user?.role === 'MERCHANT'
    ? 'Store Owner'
    : user?.role === 'SUPER_ADMIN'
    ? 'Super Admin'
    : 'Shopper'

  const displayName = staff
    ? `${staff.staffName} (${staff.businessName})`
    : user?.full_name || user?.phone || 'Authenticated User'

  return (
    <header className="sticky top-0 z-40 w-full bg-stone-950/95 border-b border-stone-800/90 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & Active Portal */}
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded bg-stone-900 border border-stone-700 flex items-center justify-center font-mono font-bold text-amber-400 text-sm">
            F
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base font-display text-stone-100">Fyndo</span>
              <span className="font-mono text-[10px] uppercase tracking-wider px-1.5 py-0.2 rounded bg-amber-950/40 text-amber-400 border border-amber-800/60 font-bold">
                {currentPortalName}
              </span>
            </div>
            <p className="text-[11px] text-stone-400 font-mono hidden sm:block">
              Nagpur & Mumbai Pilot
            </p>
          </div>
        </div>

        {/* Right Section: Active User Profile, Role Switcher & Logout */}
        <div className="flex items-center gap-3">
          {/* Quick RBAC Switcher */}
          <RoleSwitcher />

          {/* User Tag */}
          <div className="flex items-center gap-2 border border-stone-800 bg-stone-900 px-2.5 py-1 rounded-lg">
            <div className="h-5 w-5 rounded bg-stone-800 text-amber-400 flex items-center justify-center font-mono text-[10px] font-bold">
              {roleLabel.slice(0, 1)}
            </div>
            <div className="text-left font-mono text-xs">
              <p className="font-medium text-stone-200 truncate max-w-[140px] leading-tight">
                {displayName}
              </p>
              <p className="text-[10px] text-stone-400 leading-tight">
                {roleLabel}
              </p>
            </div>
          </div>

          {/* Return to Login / Logout Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="text-xs font-mono text-stone-300 hover:text-red-400"
          >
            <LogOut className="h-3.5 w-3.5 mr-1" />
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
