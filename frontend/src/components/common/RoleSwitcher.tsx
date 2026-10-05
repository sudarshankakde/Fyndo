import React from 'react'
import { UserRole } from '@/types/auth'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthSession, setStaffSession, logout } from '@/store/slices/authSlice'
import { usePermissions } from '@/hooks/usePermissions'

export const RoleSwitcher: React.FC = () => {
  const dispatch = useAppDispatch()
  const { role } = usePermissions()

  const handleRoleSelect = (selectedRole: UserRole | 'ANONYMOUS') => {
    if (selectedRole === 'ANONYMOUS') {
      dispatch(logout())
      return
    }

    if (selectedRole === 'ROLE_CASHIER') {
      dispatch(
        setStaffSession({
          accessToken: 'demo_staff_token_counter_01',
          staffId: 'stf_01',
          merchantId: 'm101-sitabuldi',
          businessName: "Haldiram's Sitabuldi",
          staffName: 'Rajesh (Counter 1)',
        })
      )
      return
    }

    const profiles: Record<Exclude<UserRole, 'ROLE_CASHIER'>, { name: string; phone: string }> = {
      MERCHANT: { name: "Haldiram's Sitabuldi (Owner)", phone: '+919876543210' },
      SHOPPER: { name: 'Pooja (Nearby Shopper)', phone: '+919123456780' },
      SUPER_ADMIN: { name: 'Admin (Nagpur Review)', phone: '+919999900000' },
    }

    dispatch(
      setAuthSession({
        accessToken: `demo_token_${selectedRole.toLowerCase()}`,
        refreshToken: 'demo_refresh_token',
        user: {
          id: `usr_${selectedRole.toLowerCase()}_01`,
          phone: profiles[selectedRole].phone,
          full_name: profiles[selectedRole].name,
          role: selectedRole,
          preferred_language: 'en',
        },
      })
    )
  }

  return (
    <div className="hidden xl:flex items-center gap-1.5 font-mono text-[10px] bg-stone-900 border border-stone-800 p-1 rounded-lg">
      <span className="text-stone-500 uppercase px-1">Role:</span>
      {(
        [
          { id: 'MERCHANT', label: 'Store Owner' },
          { id: 'ROLE_CASHIER', label: 'Counter Staff' },
          { id: 'SUPER_ADMIN', label: 'Super Admin' },
        ] as const
      ).map((item) => {
        const isActive = role === item.id
        return (
          <button
            key={item.id}
            onClick={() => handleRoleSelect(item.id)}
            className={`px-2 py-0.5 rounded transition-colors ${
              isActive
                ? 'bg-amber-500 text-stone-950 font-bold'
                : 'text-stone-400 hover:text-stone-200 hover:bg-stone-800'
            }`}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
