import React from 'react'
import { MapPin, Globe, User as UserIcon, LogOut, ShieldCheck } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { setLanguage, setAuthModalOpen } from '@/store/slices/uiSlice'
import { logout } from '@/store/slices/authSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { SupportedLanguage } from '@/types/api'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Link } from 'react-router-dom'

import { RoleSwitcher } from '@/components/common/RoleSwitcher'

export const Navbar: React.FC = () => {
  const dispatch = useAppDispatch()
  const { t, language } = useTranslation()
  const { isAuthenticated, user, staff } = useAppSelector((state) => state.auth)

  const handleLanguageChange = (lang: SupportedLanguage) => {
    dispatch(setLanguage(lang))
  }

  return (
    <header className="sticky top-0 z-40 w-full bg-stone-950/95 border-b border-stone-800/90 px-4 py-3 backdrop-blur-none">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand Identity */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="h-8 w-8 rounded bg-stone-900 border border-stone-700 flex items-center justify-center font-mono font-bold text-amber-400 text-sm group-hover:border-amber-500/60 transition-colors">
            F
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg font-display tracking-tight text-stone-100 group-hover:text-amber-400 transition-colors">
                {t.portal_title}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded bg-stone-900 text-stone-400 border border-stone-800">
                STORE
              </span>
            </div>
            <p className="text-[11px] text-stone-400 font-mono tracking-tight hidden sm:block">
              Nagpur & Mumbai
            </p>
          </div>
        </Link>

        {/* Business Console Navigation Tabs (Desktop) */}
        <nav className="hidden lg:flex items-center gap-1 border border-stone-800 bg-stone-900/60 p-1 rounded-lg text-xs font-medium">
          <Link
            to="/merchant"
            className="px-3 py-1.5 rounded hover:text-white text-stone-300 hover:bg-stone-800/80 transition-colors"
          >
            {t.merchant_studio}
          </Link>
          <Link
            to="/pos"
            className="px-3 py-1.5 rounded hover:text-white text-stone-300 hover:bg-stone-800/80 transition-colors"
          >
            {t.pos_terminal}
          </Link>
          <Link
            to="/admin"
            className="px-3 py-1.5 rounded hover:text-white text-stone-300 hover:bg-stone-800/80 transition-colors"
          >
            {t.admin_desk}
          </Link>
          <Link
            to="/app"
            className="px-3 py-1.5 rounded text-stone-400 hover:text-amber-400 hover:bg-stone-850 transition-colors flex items-center gap-1.5"
          >
            <span>{t.shopper_app}</span>
          </Link>
        </nav>

        {/* Controls: Role Switcher & Account */}
        <div className="flex items-center gap-3">
          {/* RBAC Live Role Switcher */}
          <RoleSwitcher />
          {/* Language Switcher */}
          {/* <div className="flex items-center rounded border border-stone-800 bg-stone-900 p-0.5 font-mono">
            <Globe className="h-3 w-3 text-stone-500 ml-1.5 mr-1" />
            {(['en', 'hi', 'mr'] as SupportedLanguage[]).map((lang) => (
              <button
                key={lang}
                onClick={() => handleLanguageChange(lang)}
                className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors ${
                  language === lang
                    ? 'bg-stone-800 text-amber-400 border border-stone-700'
                    : 'text-stone-400 hover:text-stone-200'
                }`}
              >
                {lang === 'en' ? 'EN' : lang === 'hi' ? 'HI' : 'MR'}
              </button>
            ))}
          </div> */}

          {/* User Account / Staff / Login */}
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              {user && (
                <div className="flex items-center gap-2 border border-stone-800 bg-stone-900 px-2.5 py-1 rounded">
                  <div className="h-5 w-5 rounded bg-stone-800 text-amber-400 flex items-center justify-center font-mono text-[10px] font-bold">
                    {user.phone.slice(-2)}
                  </div>
                  <div className="hidden sm:block text-left text-xs font-mono">
                    <p className="font-medium text-stone-200 truncate max-w-[100px]">
                      {user.full_name || user.phone}
                    </p>
                    <p className="text-[10px] text-stone-500 capitalize">
                      {user.role.toLowerCase()}
                    </p>
                  </div>
                </div>
              )}

              {staff && (
                <Badge variant="amber" className="hidden sm:inline-flex py-0.5">
                  <ShieldCheck className="h-3 w-3 mr-1" />
                  {staff.staffName}
                </Badge>
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={() => dispatch(logout())}
                title={t.logout}
                className="text-stone-400 hover:text-red-400"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => dispatch(setAuthModalOpen(true))}
            >
              <UserIcon className="h-3.5 w-3.5 mr-1.5" />
              <span>{t.login}</span>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
