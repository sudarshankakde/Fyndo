import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Store, LogOut, Globe, Phone, ChevronRight, Ticket, Check, Edit2 } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '@/store'
import { logout, updateUser } from '@/store/slices/authSlice'
import { setLanguage } from '@/store/slices/uiSlice'
import { authService } from '@/services/authService'
import { SupportedLanguage } from '@/types/api'
import { Button } from '@/components/ui/Button'

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user, refreshToken } = useAppSelector((state) => state.auth)
  const { language } = useAppSelector((state) => state.ui)

  const [isEditingName, setIsEditingName] = useState(false)
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [isSavingName, setIsSavingName] = useState(false)

  const handleLogout = async () => {
    await authService.logout(refreshToken)
    dispatch(logout())
    navigate('/login')
  }

  const handleLanguageChange = async (lang: SupportedLanguage) => {
    dispatch(setLanguage(lang))
    try {
      await authService.updateProfile({ preferred_language: lang })
    } catch {
      // Best-effort profile sync
    }
  }

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!fullName.trim()) return
    setIsSavingName(true)
    try {
      const updatedUser = await authService.updateProfile({ full_name: fullName.trim() })
      dispatch(updateUser(updatedUser))
      setIsEditingName(false)
    } catch {
      // Ignore
    } finally {
      setIsSavingName(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 font-sans text-stone-900">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-black tracking-tight text-stone-900">Shopper Profile</h1>
        <p className="text-sm text-stone-500 mt-1">Manage your Fyndo account, language preferences, and store links.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: User Card */}
        <div className="md:col-span-1 space-y-4">
          <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card text-center space-y-4">
            <div className="w-20 h-20 rounded-3xl bg-primary/10 text-primary flex items-center justify-center font-black text-2xl mx-auto shadow-inner">
              {user?.full_name ? user.full_name[0].toUpperCase() : <User className="w-10 h-10" />}
            </div>
            <div>
              {isEditingName ? (
                <form onSubmit={handleSaveName} className="space-y-2">
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs text-center border border-stone-300 rounded-xl focus:outline-none focus:ring-1 focus:ring-primary font-bold"
                    placeholder="Enter full name"
                    autoFocus
                  />
                  <div className="flex justify-center gap-1.5">
                    <button
                      type="submit"
                      disabled={isSavingName}
                      className="px-3 py-1 rounded-lg bg-primary text-white text-[11px] font-bold flex items-center gap-1"
                    >
                      <Check className="w-3 h-3" />
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsEditingName(false)}
                      className="px-3 py-1 rounded-lg bg-stone-100 text-stone-600 text-[11px] font-bold"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex items-center justify-center gap-1.5">
                  <h2 className="text-lg font-black text-stone-900 truncate">
                    {user?.full_name || 'Fyndo Shopper'}
                  </h2>
                  <button
                    onClick={() => {
                      setFullName(user?.full_name || '')
                      setIsEditingName(true)
                    }}
                    className="p-1 text-stone-400 hover:text-stone-700"
                    aria-label="Edit Name"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              <div className="flex items-center justify-center gap-1.5 text-xs text-stone-500 mt-1 font-mono">
                <Phone className="w-3.5 h-3.5" />
                <span>{user?.phone || 'Mobile not provided'}</span>
              </div>
              <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Verified Shopper
              </span>
            </div>

            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/wallet')}
                className="w-full gap-2 text-xs font-bold"
              >
                <Ticket className="w-4 h-4 text-primary" />
                <span>Open Savings Wallet</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column: Settings & Store Tools */}
        <div className="md:col-span-2 space-y-6">
          {/* Store Merchant Call to Action */}
          {user?.role === 'MERCHANT' ? (
            <div className="bg-white hover:bg-stone-50/80 border border-stone-200/80 rounded-3xl p-6 shadow-card transition-all">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
                    <Store className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-black text-stone-900">Store Manager Studio</h3>
                    <p className="text-xs text-stone-500 mt-0.5 leading-relaxed">
                      Upload store showcase videos, configure discount limits, and set up counter scanner PINs.
                    </p>
                  </div>
                </div>
                <Button onClick={() => navigate('/merchant')} variant="primary" size="sm" className="shrink-0 gap-1.5">
                  <span>Open Studio</span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Store className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-stone-900">Are you a shop owner?</h3>
                  <p className="text-xs text-stone-500">Reach nearby walk-in shoppers across Nagpur & Mumbai</p>
                </div>
              </div>
              <p className="text-xs text-stone-600 leading-relaxed">
                Publish high-converting vertical deal videos and issue verified discount vouchers to drive customer visits. Free for local merchants during the single-city pilot!
              </p>
              <Button
                onClick={() => navigate('/merchant/onboarding')}
                variant="primary"
                size="md"
                className="w-full sm:w-auto"
              >
                Register Your Store
              </Button>
            </div>
          )}

          {/* Language Preferences */}
          <div className="bg-white rounded-3xl border border-stone-200/80 p-6 shadow-card space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-stone-100 text-stone-600 flex items-center justify-center">
                <Globe className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-black text-stone-900">Interface Language</h3>
                <p className="text-xs text-stone-500">Select your preferred viewing language</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { code: 'en', label: 'English', desc: 'Default' },
                { code: 'hi', label: 'हिंदी', desc: 'Hindi' },
                { code: 'mr', label: 'मराठी', desc: 'Marathi' },
              ].map((item) => (
                <button
                  key={item.code}
                  onClick={() => handleLanguageChange(item.code as SupportedLanguage)}
                  className={`p-3 rounded-2xl text-left border transition-all ${
                    language === item.code
                      ? 'bg-primary text-white border-primary shadow-xs'
                      : 'bg-stone-50 text-stone-700 border-stone-200 hover:bg-stone-100'
                  }`}
                >
                  <p className="text-sm font-black">{item.label}</p>
                  <p className={`text-[10px] mt-0.5 ${language === item.code ? 'text-white/80' : 'text-stone-400'}`}>
                    {item.desc}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Log out */}
          <div className="pt-2">
            <button
              onClick={handleLogout}
              className="w-full bg-white hover:bg-red-50 text-red-600 border border-stone-200/80 hover:border-red-200 rounded-2xl py-3 text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-2xs"
            >
              <LogOut className="w-4 h-4" />
              <span>Log out from this browser</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
