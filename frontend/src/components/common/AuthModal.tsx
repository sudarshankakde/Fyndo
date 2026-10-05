import React, { useState } from 'react'
import { Phone, KeyRound, Sparkles, AlertCircle, UserCheck } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useAppDispatch, useAppSelector } from '@/store'
import { setAuthModalOpen } from '@/store/slices/uiSlice'
import { setAuthSession } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { useTranslation } from '@/hooks/useTranslation'
import { phoneLoginSchema, otpSchema } from '@/utils/validationSchemas'

export const AuthModal: React.FC = () => {
  const dispatch = useAppDispatch()
  const { t, language } = useTranslation()
  const isOpen = useAppSelector((state) => state.ui.isAuthModalOpen)

  const [step, setStep] = useState<'PHONE' | 'OTP'>('PHONE')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [otp, setOtp] = useState('')
  const [otpError, setOtpError] = useState<string | null>(null)
  const [testOtp, setTestOtp] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const handleClose = () => {
    dispatch(setAuthModalOpen(false))
    setStep('PHONE')
    setOtp('')
    setPhoneError(null)
    setOtpError(null)
    setServerError(null)
  }

  // onBlur validation for Phone
  const handlePhoneBlur = async () => {
    try {
      await phoneLoginSchema.validate({ phone: phoneNumber })
      setPhoneError(null)
    } catch (err: any) {
      setPhoneError(err.message)
    }
  }

  // onBlur validation for OTP
  const handleOtpBlur = async () => {
    try {
      await otpSchema.validate({ otp })
      setOtpError(null)
    } catch (err: any) {
      setOtpError(err.message)
    }
  }

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)

    try {
      await phoneLoginSchema.validate({ phone: phoneNumber })
      setPhoneError(null)
    } catch (err: any) {
      setPhoneError(err.message)
      return
    }

    const fullPhone = `+91${phoneNumber.trim()}`
    setIsLoading(true)
    try {
      const res = await authService.sendOtp(fullPhone)
      if (res.test_otp) {
        setTestOtp(res.test_otp)
      }
      setStep('OTP')
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Failed to send OTP')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)

    try {
      await otpSchema.validate({ otp })
      setOtpError(null)
    } catch (err: any) {
      setOtpError(err.message)
      return
    }

    const fullPhone = `+91${phoneNumber.trim()}`
    setIsLoading(true)
    try {
      const session = await authService.verifyOtp(fullPhone, otp, language)
      dispatch(setAuthSession(session))
      handleClose()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Incorrect verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Instant 1-Click Demo Login
  const handleFastDemoLogin = (role: 'MERCHANT' | 'SHOPPER') => {
    dispatch(
      setAuthSession({
        accessToken: `demo_token_${role.toLowerCase()}`,
        refreshToken: 'demo_refresh_token',
        user: {
          id: `usr_${role.toLowerCase()}_demo`,
          phone: '+919876543210',
          full_name: role === 'MERCHANT' ? "Haldiram's Sitabuldi" : 'Pooja (Shopper)',
          role: role,
          preferred_language: 'en',
        },
      })
    )
    handleClose()
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title={step === 'PHONE' ? t.login : t.enter_otp}
      description={
        step === 'PHONE'
          ? 'Enter your mobile number to discover nearby store deals or manage your retail store.'
          : `We sent a 6-digit verification code to +91 ${phoneNumber}`
      }
    >
      {serverError && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs font-mono">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      {step === 'PHONE' ? (
        <form onSubmit={handleSendOtp} className="space-y-4">
          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">Mobile Number</label>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-xs font-mono font-bold text-stone-400 select-none">
                +91
              </span>
              <Input
                type="tel"
                placeholder={t.phone_placeholder}
                value={phoneNumber}
                maxLength={10}
                onChange={(e) => {
                  setPhoneNumber(e.target.value.replace(/\D/g, ''))
                  if (phoneError) setPhoneError(null)
                }}
                onBlur={handlePhoneBlur}
                error={phoneError || undefined}
                className="pl-12 text-sm font-mono tracking-wider"
                autoFocus
              />
            </div>
          </div>

          <Button type="submit" variant="primary" size="md" className="w-full" isLoading={isLoading}>
            <Phone className="h-4 w-4 mr-2" />
            <span>{t.send_otp}</span>
          </Button>

          {/* Quick Demo Login Option */}
          <div className="pt-3 border-t border-stone-800 space-y-2 text-center">
            <span className="text-[11px] text-stone-400 font-mono block">Instant Demo Access</span>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleFastDemoLogin('MERCHANT')}
                className="text-xs font-mono"
              >
                Store Owner Demo
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleFastDemoLogin('SHOPPER')}
                className="text-xs font-mono"
              >
                Shopper Demo
              </Button>
            </div>
          </div>
        </form>
      ) : (
        <form onSubmit={handleVerifyOtp} className="space-y-4">
          <div className="space-y-1">
            <label className="font-mono text-xs text-stone-300 block">6-Digit Code</label>
            <Input
              type="text"
              placeholder="••••••"
              value={otp}
              maxLength={6}
              onChange={(e) => {
                setOtp(e.target.value.replace(/\D/g, ''))
                if (otpError) setOtpError(null)
              }}
              onBlur={handleOtpBlur}
              error={otpError || undefined}
              className="text-center text-xl tracking-[0.4em] font-mono font-bold"
              autoFocus
            />
          </div>

          {testOtp && (
            <div className="flex items-center justify-between p-2.5 rounded border border-stone-800 bg-stone-900 text-xs font-mono">
              <span className="text-amber-400">
                Dev OTP: <strong>{testOtp}</strong>
              </span>
              <button
                type="button"
                onClick={() => setOtp(testOtp)}
                className="text-stone-300 hover:text-white underline"
              >
                Auto-fill
              </button>
            </div>
          )}

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="md"
              className="w-1/3"
              onClick={() => setStep('PHONE')}
            >
              Back
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-2/3"
              isLoading={isLoading}
            >
              <KeyRound className="h-4 w-4 mr-2" />
              <span>{t.verify_otp}</span>
            </Button>
          </div>
        </form>
      )}
    </Dialog>
  )
}
