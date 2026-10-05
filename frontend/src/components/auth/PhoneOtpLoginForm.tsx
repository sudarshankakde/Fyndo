import React, { useState } from 'react'
import { Phone, KeyRound } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useAppDispatch } from '@/store'
import { setAuthSession } from '@/store/slices/authSlice'
import { authService } from '@/services/authService'
import { phoneLoginSchema, otpSchema } from '@/utils/validationSchemas'

interface PhoneOtpLoginFormProps {
  onServerError: (error: string | null) => void
}

export const PhoneOtpLoginForm: React.FC<PhoneOtpLoginFormProps> = ({ onServerError }) => {
  const dispatch = useAppDispatch()
  const [step, setStep] = useState<'PHONE' | 'OTP'>('PHONE')
  const [phone, setPhone] = useState('')
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [otp, setOtp] = useState('')
  const [otpError, setOtpError] = useState<string | null>(null)
  const [testOtp, setTestOtp] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handlePhoneBlur = async () => {
    try {
      await phoneLoginSchema.validate({ phone })
      setPhoneError(null)
    } catch (err: any) {
      setPhoneError(err.message)
    }
  }

  const handleOtpBlur = async () => {
    try {
      await otpSchema.validate({ otp })
      setOtpError(null)
    } catch (err: any) {
      setOtpError(err.message)
    }
  }

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    onServerError(null)

    try {
      await phoneLoginSchema.validate({ phone })
      setPhoneError(null)
    } catch (err: any) {
      setPhoneError(err.message)
      return
    }

    setIsLoading(true)
    try {
      const fullPhone = `+91${phone.trim()}`
      const res = await authService.sendOtp(fullPhone)
      if (res.test_otp) setTestOtp(res.test_otp)
      setStep('OTP')
    } catch (err: any) {
      onServerError(err.message || 'Failed to send verification code')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    onServerError(null)

    try {
      await otpSchema.validate({ otp })
      setOtpError(null)
    } catch (err: any) {
      setOtpError(err.message)
      return
    }

    setIsLoading(true)
    try {
      const fullPhone = `+91${phone.trim()}`
      const session = await authService.verifyOtp(fullPhone, otp)
      dispatch(setAuthSession(session))
    } catch (err: any) {
      onServerError(err.message || 'Incorrect verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (step === 'PHONE') {
    return (
      <form onSubmit={handleRequestOtp} className="space-y-4">
        <div className="space-y-1">
          <label className="font-mono text-xs text-stone-300 block">Registered Store Mobile</label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-xs font-mono font-bold text-stone-400 select-none">
              +91
            </span>
            <Input
              type="tel"
              placeholder="Enter 10-digit mobile number"
              value={phone}
              maxLength={10}
              onChange={(e) => {
                setPhone(e.target.value.replace(/\D/g, ''))
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
          <span>Get Verification Code</span>
        </Button>
      </form>
    )
  }

  return (
    <form onSubmit={handleVerifyOtp} className="space-y-4">
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="font-mono text-xs text-stone-300">6-Digit Code</label>
          <button
            type="button"
            onClick={() => setStep('PHONE')}
            className="text-[11px] text-amber-400 hover:text-amber-300 font-mono"
          >
            Change (+91 {phone})
          </button>
        </div>
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
        <div className="flex items-center justify-between p-2 rounded border border-stone-800 bg-stone-950 text-xs font-mono">
          <span className="text-amber-400">Dev Code: <strong>{testOtp}</strong></span>
          <button
            type="button"
            onClick={() => setOtp(testOtp)}
            className="text-stone-300 hover:text-white underline"
          >
            Auto-fill
          </button>
        </div>
      )}

      <Button type="submit" variant="primary" size="md" className="w-full" isLoading={isLoading}>
        <KeyRound className="h-4 w-4 mr-2" />
        <span>Verify & Enter Store Manager</span>
      </Button>
    </form>
  )
}
