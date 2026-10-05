import React from 'react'
import { useAppDispatch } from '@/store'
import { setAuthSession, setStaffSession } from '@/store/slices/authSlice'
import { UserRole } from '@/types/auth'

import { authService } from '@/services/authService'

export const QuickDemoAccessBar: React.FC = () => {
  const dispatch = useAppDispatch()

  const handleFastLogin = async (role: UserRole) => {
    try {
      if (role === 'ROLE_CASHIER') {
        // Try real cashier login first, or dev token
        try {
          const session = await authService.staffLogin('+919876543210', '123456')
          dispatch(setStaffSession(session))
          return
        } catch {
          // Dev fallback
        }
      }
      const session = await authService.getDevToken(role)
      dispatch(setAuthSession(session))
      return
    } catch {
      // Fallback to static session if backend is initializing
    }

    if (role === 'ROLE_CASHIER') {
      dispatch(
        setStaffSession({
          accessToken: 'demo_staff_token_counter_01',
          staffId: 'stf_01',
          merchantId: 'm101-sitabuldi',
          businessName: "Haldiram's Sitabuldi",
          staffName: 'Rajesh Sharma (Counter 1)',
        })
      )
      return
    }

    const profiles: Record<'MERCHANT' | 'SUPER_ADMIN', { name: string; phone: string }> = {
      MERCHANT: { name: "Haldiram's Sitabuldi (Store Owner)", phone: '+919876543210' },
      SUPER_ADMIN: { name: 'Admin (Nagpur Regional Desk)', phone: '+919999900000' },
    }

    if (role === 'MERCHANT' || role === 'SUPER_ADMIN') {
      dispatch(
        setAuthSession({
          accessToken: `demo_token_${role.toLowerCase()}`,
          refreshToken: 'demo_refresh_token',
          user: {
            id: `usr_${role.toLowerCase()}_demo`,
            phone: profiles[role].phone,
            full_name: profiles[role].name,
            role: role,
            preferred_language: 'en',
          },
        })
      )
    }
  }

  return (
    <div className="pt-4 border-t border-stone-800 space-y-2 text-center">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-stone-400 uppercase tracking-wider">
          Demo Direct Access
        </span>
        <span className="font-mono text-[9px] text-amber-500/80">Nagpur Pilot</span>
      </div>

      <div className="grid grid-cols-3 gap-2 font-mono text-xs">
        <button
          type="button"
          onClick={() => handleFastLogin('MERCHANT')}
          className="p-2.5 rounded border border-stone-800 bg-stone-950/60 hover:bg-stone-850 hover:border-amber-500/50 text-left transition-colors"
        >
          <strong className="text-amber-400 block text-[11px]">Store Owner</strong>
          <span className="text-[10px] text-stone-400 truncate block">Haldiram's Hub</span>
        </button>

        <button
          type="button"
          onClick={() => handleFastLogin('ROLE_CASHIER')}
          className="p-2.5 rounded border border-stone-800 bg-stone-950/60 hover:bg-stone-850 hover:border-amber-500/50 text-left transition-colors"
        >
          <strong className="text-amber-400 block text-[11px]">Counter Staff</strong>
          <span className="text-[10px] text-stone-400 truncate block">POS Terminal</span>
        </button>

        <button
          type="button"
          onClick={() => handleFastLogin('SUPER_ADMIN')}
          className="p-2.5 rounded border border-stone-800 bg-stone-950/60 hover:bg-stone-850 hover:border-amber-500/50 text-left transition-colors"
        >
          <strong className="text-stone-300 block text-[11px]">Super Admin</strong>
          <span className="text-[10px] text-stone-400 truncate block">Video Desk</span>
        </button>
      </div>
    </div>
  )
}
