import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppDispatch } from '@/store'
import { setAuthSession } from '@/store/slices/authSlice'
import { setLocation } from '@/store/slices/uiSlice'
import { authService } from '@/services/authService'
import { BETA_CITIES } from '@/config/constants'
import { UserRole } from '@/types/auth'

export const DevToolsOverlay: React.FC = () => {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [loadingRole, setLoadingRole] = useState<string | null>(null)

  const handleQuickLogin = async (role: UserRole) => {
    try {
      setLoadingRole(role)
      const session = await authService.getDevToken(role)
      dispatch(setAuthSession(session))
      setIsOpen(false)

      if (role === 'MERCHANT') {
        navigate('/merchant')
      } else if (role === 'SUPER_ADMIN') {
        navigate('/admin')
      } else if (role === 'ROLE_CASHIER') {
        navigate('/pos')
      } else {
        navigate('/')
      }
    } catch (err: any) {
      alert(`Dev login error: ${err.message}`)
    } finally {
      setLoadingRole(null)
    }
  }

  const handleSetCity = (cityKey: 'NAGPUR' | 'MUMBAI') => {
    const city = BETA_CITIES[cityKey]
    dispatch(
      setLocation({
        lat: city.center.lat,
        lon: city.center.lon,
        source: 'preset',
        city: city.name,
      })
    )
    setIsOpen(false)
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 font-sans" data-dev-only>
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-amber-400 hover:bg-amber-500 text-stone-950 font-bold px-3 py-1.5 rounded-full shadow-lg text-xs flex items-center gap-1.5 border border-amber-500 uppercase tracking-wider"
          data-dev-only
        >
          <span className="w-2 h-2 rounded-full bg-stone-950 animate-pulse" />
          DEV TOOLS
        </button>
      ) : (
        <div
          className="bg-white border-2 border-amber-400 rounded-2xl p-4 shadow-2xl w-80 text-stone-900 text-xs"
          data-dev-only
        >
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-stone-200">
            <div className="flex items-center gap-1.5 font-bold text-amber-700">
              <span className="bg-amber-400 text-stone-950 px-1.5 py-0.5 rounded text-[10px]">
                DEV
              </span>
              <span>Fast-Lane Tools</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-stone-400 hover:text-stone-700 font-bold px-2 py-0.5"
            >
              ✕
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <p className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider mb-1.5">
                Quick Dev Login
              </p>
              <div className="grid grid-cols-3 gap-1.5">
                {(['SHOPPER', 'MERCHANT', 'SUPER_ADMIN'] as UserRole[]).map((role) => (
                  <button
                    key={role}
                    onClick={() => handleQuickLogin(role)}
                    disabled={loadingRole !== null}
                    className="bg-stone-100 hover:bg-amber-50 text-stone-800 border border-stone-200 hover:border-amber-400 rounded-lg py-1.5 text-[11px] font-medium transition-colors disabled:opacity-50"
                  >
                    {loadingRole === role ? '...' : role.replace('SUPER_', '')}
                  </button>
                ))}
              </div>
              <div className="pt-1.5">
                <button
                  type="button"
                  onClick={() => {
                    navigate('/merchant/onboarding')
                    setIsOpen(false)
                  }}
                  className="w-full bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 rounded-lg py-1 text-[10px] font-bold text-center"
                >
                  📝 Open Merchant KYC Onboarding
                </button>
              </div>
            </div>

            <div>
              <p className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider mb-1.5">
                Preset Location
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  onClick={() => handleSetCity('NAGPUR')}
                  className="bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg py-1.5 text-[11px] font-medium border border-stone-200"
                >
                  📍 Sitabuldi (Nagpur)
                </button>
                <button
                  onClick={() => handleSetCity('MUMBAI')}
                  className="bg-stone-100 hover:bg-stone-200 text-stone-800 rounded-lg py-1.5 text-[11px] font-medium border border-stone-200"
                >
                  📍 Dadar (Mumbai)
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
