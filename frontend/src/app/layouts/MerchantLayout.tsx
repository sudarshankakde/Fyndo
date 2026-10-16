import React from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Store, PlusCircle, KeyRound, LogOut, ShieldCheck } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { logout } from '@/store/slices/authSlice'
import { setLanguage } from '@/store/slices/uiSlice'
import { SupportedLanguage } from '@/types/api'
import { authService } from '@/services/authService'

export const MerchantLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const { user, refreshToken } = useAppSelector((state) => state.auth)
  const { language } = useAppSelector((state) => state.ui)

  const isCurrent = (path: string) => location.pathname === path

  const handleLogout = async () => {
    await authService.logout(refreshToken)
    dispatch(logout())
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-sans text-stone-900">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 bg-white border-b border-stone-200 px-4 sm:px-8 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/merchant')}>
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center text-white font-extrabold text-lg shadow-sm">
              F
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight">Fyndo</span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
                Store Manager
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => navigate('/merchant')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                isCurrent('/merchant') ? 'bg-stone-100 text-stone-900' : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => navigate('/merchant/offers/new')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                isCurrent('/merchant/offers/new') ? 'bg-primary text-white' : 'text-stone-700 bg-primary/10 hover:bg-primary/20'
              }`}
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Post Store Video & Offer</span>
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          {/* Store Name & Verification Badge */}
          {user?.business_name && (
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>{user.business_name}</span>
            </div>
          )}

          {/* Language Switch */}
          <div className="flex items-center bg-stone-100 p-0.5 rounded-full text-xs font-bold border border-stone-200 notranslate">
            {(['en', 'hi', 'mr'] as SupportedLanguage[]).map((lang) => (
              <button
                key={lang}
                onClick={() => dispatch(setLanguage(lang))}
                className={`px-2 py-0.5 rounded-full uppercase transition-all ${
                  language === lang ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-xs font-bold text-stone-500 hover:text-stone-900 px-2.5 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Log out</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  )
}
