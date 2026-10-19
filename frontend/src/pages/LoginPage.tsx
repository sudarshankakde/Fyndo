import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Store, ShoppingBag, ShieldCheck, AlertCircle } from 'lucide-react'
import { PhoneOtpLoginForm } from '@/components/auth/PhoneOtpLoginForm'
import { useAppDispatch, useAppSelector } from '@/store'
import { setLanguage } from '@/store/slices/uiSlice'
import { SupportedLanguage } from '@/types/api'

export const LoginPage: React.FC = () => {
  const dispatch = useAppDispatch()
  const { language } = useAppSelector((state) => state.ui)
  const [intent, setIntent] = useState<'SHOPPER' | 'MERCHANT'>('SHOPPER')
  const [serverError, setServerError] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-stone-900 flex flex-col justify-between p-4 sm:p-6 lg:p-10 font-sans">
      {/* Top Bar with Home Link & Language Selector */}
      <header className="max-w-md w-full mx-auto flex items-center justify-between pb-4">
        <Link to="/" className="flex items-center gap-2 group cursor-pointer" title="Back to Home">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center text-white font-extrabold text-base shadow-xs group-hover:scale-105 transition-transform">
            F
          </div>
          <span className="font-extrabold text-xl tracking-tight text-stone-900 group-hover:text-primary transition-colors">
            Fyndo<span className="text-primary">.</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="text-xs font-bold text-stone-500 hover:text-stone-900 transition-colors hidden sm:inline-block"
          >
            ← Explore Deals
          </Link>

          {/* Trilingual Pill */}
          <div className="flex items-center bg-white border border-stone-200 p-0.5 rounded-full text-xs font-bold shadow-2xs notranslate">
            {(['en', 'hi', 'mr'] as SupportedLanguage[]).map((lang) => (
              <button
                key={lang}
                onClick={() => dispatch(setLanguage(lang))}
                className={`px-2.5 py-1 rounded-full uppercase transition-all ${
                  language === lang ? 'bg-primary text-white shadow-xs' : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Login Card */}
      <main className="max-w-md w-full mx-auto my-auto py-4">
        <div className="bg-white rounded-3xl border border-stone-200 p-6 sm:p-8 shadow-card space-y-6">
          <div>
            <h1 className="text-2xl font-extrabold text-stone-900 tracking-tight">
              {intent === 'SHOPPER' ? 'Discover Local Deals' : 'Manage Your Store'}
            </h1>
            <p className="text-xs text-stone-500 mt-1">
              {intent === 'SHOPPER'
                ? 'Save exclusive discounts from verified local shops in your city.'
                : 'Connect with nearby shoppers and grow your in-store walk-in sales.'}
            </p>
          </div>

          {/* Intent Toggle */}
          <div className="grid grid-cols-2 p-1 bg-stone-100 rounded-2xl border border-stone-200 text-xs font-bold">
            <button
              type="button"
              onClick={() => {
                setIntent('SHOPPER')
                setServerError(null)
              }}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl transition-all ${
                intent === 'SHOPPER'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              <ShoppingBag className="w-4 h-4" />
              <span>For Shoppers</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setIntent('MERCHANT')
                setServerError(null)
              }}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl transition-all ${
                intent === 'MERCHANT'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-500 hover:text-stone-900'
              }`}
            >
              <Store className="w-4 h-4" />
              <span>Store Owners</span>
            </button>
          </div>

          {/* Server Error Alert */}
          {serverError && (
            <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{serverError}</span>
            </div>
          )}

          {/* Unified Phone + OTP Form */}
          <PhoneOtpLoginForm intent={intent} onServerError={setServerError} />

          {/* Counter Scanner Staff Link */}
          <div className="pt-4 border-t border-stone-100 text-center">
            <Link
              to="/pos/login"
              className="text-xs font-bold text-stone-600 hover:text-stone-900 hover:underline"
            >
              Cashier or Store Staff? <span className="text-emerald-700">Open Counter Scanner →</span>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-md w-full mx-auto text-center pt-4 text-xs font-medium text-stone-400">
        <span>© 2026 Fyndo Technologies • Nagpur & Mumbai Pilot</span>
      </footer>
    </div>
  )
}
