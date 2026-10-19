import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { QrCode, Delete, AlertCircle, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useAppDispatch } from '@/store'
import { setStaffSession } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'

export const PosLoginPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const savedPhone = (typeof window !== 'undefined' && localStorage.getItem('fyndo_pos_store_phone')) || ''
  const [storePhone, setStorePhone] = useState(savedPhone)
  const [pin, setPin] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleDigitPress = (digit: string) => {
    if (pin.length < 6) {
      const nextPin = pin + digit
      setPin(nextPin)
      if (nextPin.length === 6) {
        handleLogin(nextPin)
      }
    }
  }

  const handleDelete = () => {
    setPin((prev) => prev.slice(0, -1))
    setErrorMessage(null)
  }

  const handleLogin = async (pinToSubmit?: string) => {
    const finalPin = pinToSubmit || pin
    if (finalPin.length !== 6) return

    const cleanedPhone = storePhone.trim()
    if (!/^[6-9]\d{9}$/.test(cleanedPhone)) {
      setErrorMessage('Enter the 10-digit registered store phone number.')
      return
    }

    setIsLoading(true)
    setErrorMessage(null)

    try {
      localStorage.setItem('fyndo_pos_store_phone', cleanedPhone)
      const session = await authService.staffLogin(`+91${cleanedPhone}`, finalPin)
      dispatch(setStaffSession(session))
      navigate('/pos')
    } catch {
      setErrorMessage('Phone or PIN is incorrect. Please check with the store owner.')
      setPin('')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-stone-900 flex flex-col justify-between p-4 sm:p-6 font-sans">
      <header className="max-w-sm w-full mx-auto flex items-center justify-between pb-2">
        <Link to="/login" className="flex items-center gap-1.5 text-xs font-bold text-stone-500 hover:text-stone-900">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Login</span>
        </Link>
        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
          Counter Terminal
        </span>
      </header>

      <main className="max-w-sm w-full mx-auto my-auto py-2">
        <div className="bg-white rounded-3xl border border-stone-200 p-6 shadow-card space-y-5">
          <div className="text-center">
            <div className="w-12 h-12 rounded-2xl bg-emerald-600 text-white flex items-center justify-center mx-auto mb-3 shadow-md shadow-emerald-600/20">
              <QrCode className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-extrabold text-stone-900 tracking-tight">Counter Staff Login</h1>
            <p className="text-xs text-stone-500 mt-1">Enter your store phone and 6-digit staff PIN to start scanning.</p>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Store Mobile Input */}
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-stone-600 uppercase tracking-wider block">Store Phone Number</label>
            <div className="relative flex items-center">
              <span className="absolute left-3 text-xs font-bold text-stone-400 select-none">+91</span>
              <input
                type="tel"
                inputMode="tel"
                maxLength={10}
                value={storePhone}
                onChange={(e) => setStorePhone(e.target.value.replace(/\D/g, ''))}
                placeholder="Enter 10-digit store number"
                className="h-10 w-full rounded-xl border border-stone-200 bg-white pl-10 pr-3 text-xs font-semibold text-stone-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 shadow-2xs"
              />
            </div>
          </div>

          {/* 6 Dots PIN Indicator */}
          <div className="space-y-2 text-center pt-1">
            <span className="text-[11px] font-bold text-stone-600 uppercase tracking-wider block">6-Digit Counter PIN</span>
            <div className="flex justify-center gap-3 py-2">
              {[0, 1, 2, 3, 4, 5].map((index) => (
                <div
                  key={index}
                  className={`w-3.5 h-3.5 rounded-full border transition-all ${
                    pin.length > index
                      ? 'bg-emerald-600 border-emerald-600 scale-110'
                      : 'border-stone-300 bg-stone-100'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Touch-Friendly Numeric Keypad */}
          <div className="grid grid-cols-3 gap-2 pt-2">
            {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((digit) => (
              <button
                key={digit}
                type="button"
                onClick={() => handleDigitPress(digit)}
                disabled={isLoading}
                className="h-12 rounded-xl bg-stone-50 hover:bg-stone-100 border border-stone-200 text-lg font-bold text-stone-900 active:scale-95 transition-all shadow-2xs"
              >
                {digit}
              </button>
            ))}
            <div />
            <button
              type="button"
              onClick={() => handleDigitPress('0')}
              disabled={isLoading}
              className="h-12 rounded-xl bg-stone-50 hover:bg-stone-100 border border-stone-200 text-lg font-bold text-stone-900 active:scale-95 transition-all shadow-2xs"
            >
              0
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={isLoading || pin.length === 0}
              className="h-12 rounded-xl bg-stone-50 hover:bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-600 active:scale-95 transition-all shadow-2xs disabled:opacity-40"
            >
              <Delete className="w-5 h-5" />
            </button>
          </div>
        </div>
      </main>

      <footer className="max-w-sm w-full mx-auto text-center text-[11px] font-medium text-stone-400">
        Fyndo Cashier Station • Secure In-Store Verification
      </footer>
    </div>
  )
}
