import React, { useState } from 'react'
import { ShieldCheck, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { LoginHeroSection } from '@/components/auth/LoginHeroSection'
import { PhoneOtpLoginForm } from '@/components/auth/PhoneOtpLoginForm'
import { CashierPinLoginForm } from '@/components/auth/CashierPinLoginForm'
import { QuickDemoAccessBar } from '@/components/auth/QuickDemoAccessBar'

export const LoginPage: React.FC = () => {
  const [loginMode, setLoginMode] = useState<'PHONE_OTP' | 'CASHIER_PIN'>('PHONE_OTP')
  const [serverError, setServerError] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100 flex flex-col justify-between p-4 sm:p-8 lg:p-12 font-sans selection:bg-amber-500 selection:text-stone-950">
      {/* Brand Header */}
      <header className="flex items-center justify-between max-w-6xl w-full mx-auto pb-6 border-b border-stone-800/80">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded bg-stone-900 border border-stone-700 flex items-center justify-center font-mono font-bold text-amber-400 text-sm">
            F
          </div>
          <div>
            <span className="font-bold text-lg font-display text-stone-100 tracking-tight block">
              Fyndo
            </span>
            <span className="text-[10px] font-mono text-stone-500 uppercase tracking-widest">
              Nagpur & Mumbai Pilot
            </span>
          </div>
        </div>

        <Badge variant="outline" className="hidden sm:inline-flex py-1 text-[11px] font-mono">
          <ShieldCheck className="h-3 w-3 mr-1 text-amber-400" />
          Single-City Retail Platform
        </Badge>
      </header>

      {/* Asymmetric Split Layout: Left Story / Right Auth Form */}
      <main className="max-w-6xl w-full mx-auto my-auto py-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        {/* Left Column (7 cols): Editorial Typography & Product Promise */}
        <LoginHeroSection />

        {/* Right Column (5 cols): Authentication Terminal */}
        <div className="lg:col-span-5">
          <div className="surface-card rounded-xl border border-stone-800 bg-stone-900/90 p-6 sm:p-7 space-y-5">
            {/* Mode Switcher Tabs */}
            <div className="flex rounded-lg bg-stone-950 border border-stone-800 p-1 font-mono text-xs">
              <button
                type="button"
                onClick={() => {
                  setLoginMode('PHONE_OTP')
                  setServerError(null)
                }}
                className={`flex-1 py-1.5 rounded transition-colors ${
                  loginMode === 'PHONE_OTP'
                    ? 'bg-stone-850 text-amber-400 font-bold border border-stone-700'
                    : 'text-stone-400 hover:text-stone-200'
                }`}
              >
                Store Owner OTP
              </button>
              <button
                type="button"
                onClick={() => {
                  setLoginMode('CASHIER_PIN')
                  setServerError(null)
                }}
                className={`flex-1 py-1.5 rounded transition-colors ${
                  loginMode === 'CASHIER_PIN'
                    ? 'bg-stone-850 text-amber-400 font-bold border border-stone-700'
                    : 'text-stone-400 hover:text-stone-200'
                }`}
              >
                Counter Staff PIN
              </button>
            </div>

            {/* Error Notification */}
            {serverError && (
              <div className="p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs font-mono flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{serverError}</span>
              </div>
            )}

            {/* Form */}
            {loginMode === 'PHONE_OTP' ? (
              <PhoneOtpLoginForm onServerError={setServerError} />
            ) : (
              <CashierPinLoginForm onServerError={setServerError} />
            )}

            {/* Quick Demo Access Bar */}
            <QuickDemoAccessBar />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl w-full mx-auto pt-6 border-t border-stone-800/80 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-stone-400">
        <span>© 2026 Fyndo Technologies • Single-City Beta (Nagpur / Mumbai)</span>
        <span>Audio Policy: Raw Camera Audio Only</span>
      </footer>
    </div>
  )
}
