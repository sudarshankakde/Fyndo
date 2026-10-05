import React, { useState } from 'react'
import { QrCode, KeyRound, AlertCircle, Sparkles } from 'lucide-react'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { authService } from '@/services/authService'
import { useAppDispatch } from '@/store'
import { setStaffSession } from '@/store/slices/authSlice'
import { useTranslation } from '@/hooks/useTranslation'
import { phoneLoginSchema, otpSchema } from '@/utils/validationSchemas'

interface PosLoginModalProps {
  isOpen: boolean
  onClose: () => void
}

export const PosLoginModal: React.FC<PosLoginModalProps> = ({ isOpen, onClose }) => {
  const dispatch = useAppDispatch()
  const { t } = useTranslation()

  const [storePhone, setStorePhone] = useState('')
  const [phoneError, setPhoneError] = useState<string | null>(null)
  const [pin, setPin] = useState('')
  const [pinError, setPinError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const handlePhoneBlur = async () => {
    try {
      await phoneLoginSchema.validate({ phone: storePhone })
      setPhoneError(null)
    } catch (err: any) {
      setPhoneError(err.message)
    }
  }

  const handlePinBlur = async () => {
    try {
      await otpSchema.validate({ otp: pin })
      setPinError(null)
    } catch (err: any) {
      setPinError(err.message)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)

    try {
      await phoneLoginSchema.validate({ phone: storePhone })
      await otpSchema.validate({ otp: pin })
    } catch (err: any) {
      setServerError('Please correct the highlighted fields.')
      return
    }

    setIsLoading(true)
    try {
      const fullPhone = `+91${storePhone.trim()}`
      const staffSession = await authService.staffLogin(fullPhone, pin)
      dispatch(setStaffSession(staffSession))
      onClose()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'Invalid store phone or PIN')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDemoStaffLogin = () => {
    dispatch(
      setStaffSession({
        accessToken: 'demo_staff_token_counter_01',
        staffId: 'stf_01',
        merchantId: 'm101-sitabuldi',
        businessName: "Haldiram's Sitabuldi",
        staffName: 'Rajesh Sharma (Counter 1)',
      })
    )
    onClose()
  }

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <QrCode className="h-5 w-5 text-amber-400" />
          <span>{t.staff_login}</span>
        </div>
      }
      description="Enter store phone number and your 6-digit cashier PIN to open the counter scanner."
      className="max-w-sm"
    >
      {serverError && (
        <div className="mb-4 flex items-center gap-2 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs font-mono">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs font-mono text-stone-300 mb-1 block">
            Store Owner Phone
          </label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-xs font-mono font-bold text-stone-400">
              +91
            </span>
            <Input
              type="tel"
              placeholder="10-digit mobile number"
              value={storePhone}
              maxLength={10}
              onChange={(e) => {
                setStorePhone(e.target.value.replace(/\D/g, ''))
                if (phoneError) setPhoneError(null)
              }}
              onBlur={handlePhoneBlur}
              error={phoneError || undefined}
              className="pl-12 text-sm font-mono tracking-wider"
              autoFocus
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-mono text-stone-300 mb-1 block">
            {t.enter_staff_pin}
          </label>
          <Input
            type="password"
            placeholder="••••••"
            value={pin}
            maxLength={6}
            onChange={(e) => {
              setPin(e.target.value.replace(/\D/g, ''))
              if (pinError) setPinError(null)
            }}
            onBlur={handlePinBlur}
            error={pinError || undefined}
            className="text-center text-xl tracking-[0.4em] font-mono font-bold"
          />
        </div>

        <Button type="submit" variant="primary" size="md" className="w-full mt-2" isLoading={isLoading}>
          <KeyRound className="h-4 w-4 mr-2" />
          <span>Open Counter Scanner</span>
        </Button>

        {/* Instant Demo Staff Shortcut */}
        <div className="pt-3 border-t border-stone-800 text-center">
          <button
            type="button"
            onClick={handleDemoStaffLogin}
            className="text-xs text-amber-400 hover:text-amber-300 font-mono underline inline-flex items-center gap-1"
          >
            <Sparkles className="h-3 w-3" />
            <span>1-Click Demo Cashier Terminal</span>
          </button>
        </div>
      </form>
    </Dialog>
  )
}
