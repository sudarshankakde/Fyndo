import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, RotateCw, Edit2, Zap } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthSession, updateUser } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { getSafeRedirect } from '@/utils/safeRedirect'

interface PhoneOtpLoginFormProps {
  intent: 'SHOPPER' | 'MERCHANT'
  onServerError: (error: string | null) => void
}

export const PhoneOtpLoginForm: React.FC<PhoneOtpLoginFormProps> = ({ intent, onServerError }) => {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { language } = useAppSelector((state) => state.ui)

  const [step, setStep] = useState<'PHONE' | 'OTP' | 'NAME_PROMPT'>('PHONE')
  const [phone, setPhone] = useState('')
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', ''])
  const [testOtp, setTestOtp] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [secondsRemaining, setSecondsRemaining] = useState(120)
  const [resendCooldown, setResendCooldown] = useState(30)
  const [fullName, setFullName] = useState('')

  const otpInputsRef = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>
    if (step === 'OTP' && secondsRemaining > 0) {
      timer = setInterval(() => {
        setSecondsRemaining((prev) => prev - 1)
        setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0))
      }, 1000)
    }
    return () => clearInterval(timer)
  }, [step, secondsRemaining])

  const finishLogin = (role: string) => {
    const rawNext = searchParams.get('next')
    if (rawNext) {
      navigate(getSafeRedirect(rawNext))
      return
    }
    if (intent === 'MERCHANT' || role === 'MERCHANT') {
      navigate(role === 'MERCHANT' ? '/merchant' : '/merchant/onboarding')
    } else {
      navigate('/')
    }
  }

  const handleSendOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    onServerError(null)
    const cleaned = phone.trim()
    if (!/^[6-9]\d{9}$/.test(cleaned)) {
      onServerError('Enter a valid 10-digit mobile number')
      return
    }
    setIsLoading(true)
    try {
      const res = await authService.sendOtp(`+91${cleaned}`)
      if (res.test_otp) setTestOtp(res.test_otp)
      setStep('OTP')
      setSecondsRemaining(120)
      setResendCooldown(30)
    } catch (err: any) {
      onServerError(err.message || 'Unable to send verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (codeToVerify?: string) => {
    const code = codeToVerify || otpDigits.join('')
    if (code.length !== 6) return
    setIsLoading(true)
    onServerError(null)
    try {
      const session = await authService.verifyOtp(`+91${phone.trim()}`, code, language)
      dispatch(setAuthSession(session))
      if (!session.user.full_name) {
        setStep('NAME_PROMPT')
      } else {
        finishLogin(session.user.role)
      }
    } catch (err: any) {
      onServerError(err.message || 'Incorrect verification code. Please check and try again.')
      setOtpDigits(['', '', '', '', '', ''])
      otpInputsRef.current[0]?.focus()
    } finally {
      setIsLoading(false)
    }
  }

  const handleDevBypass = async () => {
    setIsLoading(true)
    onServerError(null)
    try {
      const devPhone = phone.trim() ? `+91${phone.trim()}` : undefined
      const session = await authService.getDevToken(intent, devPhone)
      dispatch(setAuthSession(session))
      finishLogin(session.user.role)
    } catch (err: any) {
      onServerError(err.message || 'Dev bypass failed.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOtpChange = (index: number, val: string) => {
    const char = val.slice(-1)
    if (char && !/^\d$/.test(char)) return
    const newDigits = [...otpDigits]
    newDigits[index] = char
    setOtpDigits(newDigits)
    if (char && index < 5) otpInputsRef.current[index + 1]?.focus()
    if (newDigits.every((d) => d !== '')) handleVerifyOtp(newDigits.join(''))
  }

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      otpInputsRef.current[index - 1]?.focus()
    }
  }

  const handleSaveName = async () => {
    if (fullName.trim()) {
      try {
        const updated = await authService.updateProfile({ full_name: fullName.trim() })
        dispatch(updateUser(updated))
      } catch {
        // non-blocking
      }
    }
    finishLogin(intent)
  }

  const devBypassBtn = import.meta.env.DEV && (
    <button
      type="button"
      onClick={handleDevBypass}
      disabled={isLoading}
      className="w-full py-2.5 px-3 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-2xs mt-2"
    >
      <Zap className="w-3.5 h-3.5 text-amber-600 fill-amber-500" />
      <span>One-Click Dev Login as {intent === 'SHOPPER' ? 'Shopper' : 'Store Owner'} (Bypass OTP)</span>
    </button>
  )

  if (step === 'NAME_PROMPT') {
    return (
      <div className="space-y-4">
        <div className="p-3.5 bg-primary/5 rounded-2xl border border-primary/15">
          <span className="text-[10px] font-bold tracking-wider uppercase text-primary">Step 2 of 2 • Profile Setup</span>
          <h2 className="text-base font-extrabold text-stone-900 mt-0.5">What is your full name?</h2>
          <p className="text-xs text-stone-500 mt-0.5">Your name helps local store cashiers recognize your coupon passes.</p>
        </div>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="e.g. Rahul Sharma"
          className="h-11 w-full rounded-xl border border-stone-200 bg-white px-3.5 text-sm font-semibold text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          autoFocus
        />
        <div className="flex gap-2 pt-1">
          <Button onClick={handleSaveName} className="flex-1">Save & Go to Deals</Button>
          <Button variant="ghost" onClick={() => finishLogin(intent)}>Skip for now</Button>
        </div>
      </div>
    )
  }

  if (step === 'PHONE') {
    return (
      <form onSubmit={handleSendOtp} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-stone-700 block">Mobile Number</label>
          <div className="relative flex items-center">
            <span className="absolute left-3.5 text-sm font-bold text-stone-500 select-none">+91</span>
            <input
              type="tel"
              inputMode="tel"
              maxLength={10}
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
              placeholder="Enter 10-digit mobile number"
              className="h-11 w-full rounded-xl border border-stone-200 bg-white pl-12 pr-3.5 text-sm font-semibold text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
              autoFocus
            />
          </div>
        </div>

        <Button type="submit" isLoading={isLoading} className="w-full gap-2 py-3">
          <span>Get Verification Code</span>
          <ArrowRight className="w-4 h-4" />
        </Button>

        {devBypassBtn}
      </form>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-1">
        <div>
          <span className="text-xs font-medium text-stone-500">Code sent to </span>
          <span className="text-xs font-bold text-stone-900">+91 {phone}</span>
        </div>
        <button
          onClick={() => { setStep('PHONE'); setOtpDigits(['', '', '', '', '', '']) }}
          className="text-xs font-bold text-primary flex items-center gap-1 hover:underline"
        >
          <Edit2 className="w-3 h-3" />
          <span>Change</span>
        </button>
      </div>

      <div className="flex justify-between gap-1.5 sm:gap-2">
        {otpDigits.map((digit, idx) => (
          <input
            key={idx}
            ref={(el) => { otpInputsRef.current[idx] = el }}
            type="tel"
            inputMode="numeric"
            maxLength={1}
            autoComplete="one-time-code"
            value={digit}
            onChange={(e) => handleOtpChange(idx, e.target.value)}
            onKeyDown={(e) => handleOtpKeyDown(idx, e)}
            className="w-11 h-12 text-center text-lg font-extrabold rounded-xl border border-stone-200 bg-white text-stone-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary shadow-2xs"
          />
        ))}
      </div>

      {testOtp && (
        <button
          type="button"
          onClick={() => {
            const digits = testOtp.split('').slice(0, 6)
            setOtpDigits(digits)
            handleVerifyOtp(testOtp)
          }}
          className="w-full py-1.5 px-3 bg-amber-50 text-amber-800 border border-amber-300 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 hover:bg-amber-100"
          data-dev-only
        >
          <span className="px-1 py-0.2 rounded bg-amber-400 text-stone-950 text-[10px]">DEV</span>
          <span>Autofill Dev Code ({testOtp})</span>
        </button>
      )}

      <div className="flex items-center justify-between text-xs text-stone-500 pt-1">
        <span>Code expires in: {Math.floor(secondsRemaining / 60)}:{secondsRemaining % 60 < 10 ? '0' : ''}{secondsRemaining % 60}</span>
        {resendCooldown > 0 ? (
          <span>Resend in {resendCooldown}s</span>
        ) : (
          <button
            onClick={() => handleSendOtp()}
            disabled={isLoading}
            className="font-bold text-primary hover:underline flex items-center gap-1"
          >
            <RotateCw className="w-3 h-3" />
            <span>Resend Code</span>
          </button>
        )}
      </div>

      <Button
        onClick={() => handleVerifyOtp()}
        disabled={otpDigits.some((d) => d === '') || isLoading}
        isLoading={isLoading}
        className="w-full py-3"
      >
        Verify & Continue
      </Button>

      {devBypassBtn}
    </div>
  )
}
